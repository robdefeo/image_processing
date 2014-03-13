#!/usr/bin/env python

'''

Usage:
   categorize.py
'''

import numpy as np
import cv2
from os import listdir
from os.path import isfile, join
from numpy.linalg import norm
from common import autoCrop, clock, mosaic, preprocess_hog, preprocess_item_surf, shoeCategory, idCategory
from models import KNearest, SVM, RTrees, Boost, MLP
from pymongo import MongoClient

SZ = 100 # size of each digit is SZ x SZ
mosaic_SZ = 50

contentTypeExtension = {
  "image/jpeg": ".jpg"
}

def processImage(f):
  # print 'action=processing,file=%s' % (f)
  
  
  # gray = cv2.resize(cv2.imread(f, cv2.COLOR_BGR2GRAY), (SZ,SZ))
  # blur = cv2.GaussianBlur(gray,(5,5),2 )
  # thresh = cv2.adaptiveThreshold(blur,255,1,1,11,1)
  # blur_thresh = cv2.GaussianBlur(thresh,(5,5),5)
  # return blur_thresh
  # gray = cv2.imread(f, cv2.COLOR_BGR2GRAY)
  # blur = cv2.GaussianBlur(gray,(5,5),2 )
  # flag, thresh = cv2.threshold(blur, 120, 255, cv2.THRESH_BINARY)
  # flag, thresh = cv2.threshold(cv2.GaussianBlur(cv2.resize(cv2.imread(f, cv2.COLOR_BGR2GRAY), (SZ,SZ)),(1,1),1000), 120, 255, cv2.THRESH_BINARY)
  # return thresh
  # return cv2.resize(thresh, (SZ,SZ))
  # return cv2.adaptiveThreshold(cv2.resize(cv2.imread(f, cv2.CV_LOAD_IMAGE_GRAYSCALE), (SZ,SZ)),255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
  return cv2.resize(autoCrop(cv2.imread(f, cv2.CV_LOAD_IMAGE_GRAYSCALE)), (SZ,SZ))

def load_all_shoes():
  conn = MongoClient('mongodb://localhost')
  db = conn.getter
  shoes = []
  labels = []
  ids = []
  docs = db.shoes.find({ 
      "shoe.images": { 
        "$elemMatch" : {
          "_id": { 
            "$exists": True 
          }
        }
      }
    },
    { 
      "shoe": 1
    }    
  ).limit(4000)
  for doc in docs:
    # cv2.resize(cv2.imread(f, cv2.CV_LOAD_IMAGE_GRAYSCALE), (SZ,SZ))
    if len(doc["shoe"]["images"]) == 7:
      for image in doc["shoe"]["images"]:    
        if 'z' in image and image["z"] == 90 and 'y' in image and image["y"] == 0:
          cat = doc["shoe"]["categories"][len(doc["shoe"]["categories"]) - 1]
          # if cat in ['Heels', "Flats", "Sandals", "Boots"]:
          # print doc["_id"]["_id"];
          # try:
          f = "/getter_data/images/" + str(image["_id"]) + contentTypeExtension[image["content-type"]]
          shoes.append(processImage(f))
          labels.append(shoeCategory[cat])
          ids.append(image["_id"])
          # except Exception, e:
          #             print 'action=processingFile,_id=%s,file=%s,error=%s' % (doc["_id"]["_id"], f, e)
          #             raise e
          #           
            
  
  print "datasetSize=%d" % (len(shoes))
  return np.array(shoes), np.array(labels), np.array(ids)

def deskew(img):
    m = cv2.moments(img)
    if abs(m['mu02']) < 1e-2:
        return img.copy()
    skew = m['mu11']/m['mu02']
    M = np.float32([[1, skew, -0.5*SZ*skew], [0, 1, 0]])
    img = cv2.warpAffine(img, M, (SZ, SZ), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR)
    return img

def evaluate_model(model, items, samples, labels):
    resp = model.predict(samples)
    err = (labels != resp).mean()
    print 'error: %.2f %%' % (err*100)

    confusion = np.zeros((len(shoeCategory), len(shoeCategory)), np.int32)
    for i, j in zip(labels, resp):
        confusion[i, j] += 1
    print 'confusion matrix:'
    print confusion
    print

    vis = []
    for img, guess, actual in zip(items, resp, labels):
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.putText(img, idCategory[int(guess)], (0,7), cv2.FONT_HERSHEY_SIMPLEX, 0.35, 255)
        cv2.putText(img, idCategory[int(actual)], (0,15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, 255)
        # cv2.putText(img,"actual=" + idCategory[int(guess)], (0,15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, 255)
        if not guess == actual:
            img[...,:2] = 0
        vis.append(img)
    return mosaic(mosaic_SZ, vis), (err*100)

def preprocessShoes():
  shoes, labels, ids = load_all_shoes()  
      
  print 'preprocessing...'
  # shuffle digits
  rand = np.random.RandomState(321)
  shuffle = rand.permutation(len(shoes))
  shoes, labels, ids = shoes[shuffle], labels[shuffle], ids[shuffle]
  print 'creating datasets...'
  # shoes = map(deskew, shoes)
  samples = preprocess_hog(shoes)
  
  return shoes, samples, labels


        
if __name__ == '__main__':
  print __doc__
  shoes, samples, labels = preprocessShoes()

  print 'creating mosaic...'
  train_n = int(0.9*len(samples))

  shoes_train, shoes_test = np.split(shoes, [train_n])
  samples_train, samples_test = np.split(samples, [train_n])
  labels_train, labels_test = np.split(labels, [train_n])

  for label in shoeCategory.values():
    images = [i for i, l in zip(shoes_test, labels_test) if (l == label)]
    if (len(images) > 0):
      cv2.imwrite('out/test_' + idCategory[label]  + '_set.jpg', mosaic(20, images))      
  
  for label in shoeCategory.values():
    images = [i for i, l in zip(shoes_test, labels_test) if (l == label)]
    if (len(images) > 0):
      cv2.imwrite('out/test_' + idCategory[label]  + '_set.jpg', mosaic(20, images))      
 
  cv2.imwrite('out/test_set.jpg', mosaic(20, shoes_test))
  cv2.imwrite('out/train_set.jpg', mosaic(20, shoes_train))
  
  
  print 'training KNearest...'
  model = KNearest(k=4)
  model.train(samples_train, labels_train)
  vis, knearestError = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/KNearest_test_' + str(SZ) + '.jpg', vis)
  # print 'saving KNearest as "shoes_svm_' + str(SZ) + '.dat"...'
  # model.save('out/shoes_KNearest_' + str(SZ) + '.dat')
  
  print 'training SVM...'
  model = SVM(C=2.67, gamma=5.383)
  model.train(samples_train, labels_train)
  vis, svmError = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/SVM_test_' + str(SZ) + '.jpg', vis)
  print 'saving SVM as "shoes_svm_' + str(SZ) + '.dat"...'
  model.save('out/shoes_svm_' + str(SZ) + '.dat')
  
  print 'training RTrees...'
  model = RTrees()
  model.train(samples_train, labels_train)
  vis, rtreesError = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/rtrees_test_' + str(SZ) + '.jpg', vis)
  print 'saving RTrees as "shoes_rtrees_' + str(SZ) + '.dat"...'
  model.save('out/shoes_rtrees_' + str(SZ) + '.dat')
  
  print 'training Boost...'
  model = Boost()
  model.train(samples_train, labels_train)
  vis, boostError = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/boost_test_' + str(SZ) + '.jpg', vis)
  print 'saving Boost as "shoes_boost_' + str(SZ) + '.dat"...'
  model.save('out/shoes_boost_' + str(SZ) + '.dat')
  
  print 'training MLP...'
  model = MLP()
  model.train(samples_train, labels_train)
  vis, mlpError = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/mlp_test_' + str(SZ) + '.jpg', vis)
  print 'saving MLP as "shoes_mlp_' + str(SZ) + '.dat"...'
  model.save('out/shoes_mlp_' + str(SZ) + '.dat')
  
  print '%s,%s,%s,%s,%s,%s' % (len(shoes), knearestError, svmError, rtreesError, boostError, mlpError)
  
  