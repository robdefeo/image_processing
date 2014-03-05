#!/usr/bin/env python

'''

Usage:
   categorise.py
'''

import numpy as np
import cv2
from os import listdir
from os.path import isfile, join
from numpy.linalg import norm
from common import clock, mosaic, preprocess_hog, preprocess_item, shoeCategory
from models import KNearest, SVM, RTrees

SZ = 100 # size of each digit is SZ x SZ
mosaic_SZ = 50


def processImage(f):
  # orig
  
  return cv2.resize(cv2.imread(f, cv2.CV_LOAD_IMAGE_GRAYSCALE), (SZ,SZ))
  
def load_shoes_directory(pn, category):
  # files = listdir(join(pn,category))[:500]
  files = listdir(join(pn,category))
  print 'action=loading,categoryName=%s,itemCount=%d' % (category, len(files))
  
  images =  [processImage(join(pn,category,f)) for f in files if isfile(join(pn,category,f))]
  # images =  [join(pn,category,f) for f in listdir(join(pn,category))[:3] if isfile(join(pn,category,f))]
  # ss = images, np.repeat(category, len(images))
  # print ss(0)
  return images, np.repeat(shoeCategory[category], len(images))
  
def load_shoes(pn):
  print 'loading "%s" ...' % pn
  shoes, labels = [], []
  
  for d in listdir(pn):
    if not isfile(join(pn,d)) and len(listdir(join(pn,d))) > 100:
      ds = load_shoes_directory(pn,d)
      shoes.extend(ds[0])
      labels.extend(ds[1])

  shoes = np.array(shoes)
  labels = np.array(labels)
  
  # for idx, val in enumerate(shoes):
  #   cv2.imwrite("out/shoes/loaded/" + str(labels[idx]) + "_" + str(idx) + ".jpg", shoes[idx])
  return shoes, labels


def deskew(img):
    m = cv2.moments(img)
    if abs(m['mu02']) < 1e-2:
        return img.copy()
    skew = m['mu11']/m['mu02']
    M = np.float32([[1, skew, -0.5*SZ*skew], [0, 1, 0]])
    img = cv2.warpAffine(img, M, (SZ, SZ), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR)
    return img








def evaluate_model(model, digits, samples, labels):
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
    for img, flag in zip(digits, resp == labels):
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        if not flag:
            img[...,:2] = 0
        vis.append(img)
    return mosaic(mosaic_SZ, vis)
        
if __name__ == '__main__':
  print __doc__
  shoes, labels = load_shoes("../data/category/")
      
  print 'preprocessing...'
  # shuffle digits
  rand = np.random.RandomState(321)
  shuffle = rand.permutation(len(shoes))
  shoes, labels = shoes[shuffle], labels[shuffle]
    
  print 'creating datasets...'
  # shoes = map(deskew, shoes)
  samples = preprocess_hog(shoes)
  
      
  print 'creating mosaic...'
  train_n = int(0.9*len(samples))
  cv2.imwrite('out/test_set.jpg', mosaic(10, shoes[train_n:]))
  shoes_train, shoes_test = np.split(shoes, [train_n])
  samples_train, samples_test = np.split(samples, [train_n])
  labels_train, labels_test = np.split(labels, [train_n])
  
  
  print 'training KNearest...'
  model = KNearest(k=4)
  model.train(samples_train, labels_train)
  vis = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/KNearest_test_' + str(SZ) + '.jpg', vis)
  # print 'saving KNearest as "shoes_svm_' + str(SZ) + '.dat"...'
  # model.save('out/shoes_KNearest_' + str(SZ) + '.dat')
  
  print 'training SVM...'
  model = SVM(C=2.67, gamma=5.383)
  model.train(samples_train, labels_train)
  vis = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/SVM_test_' + str(SZ) + '.jpg', vis)
  print 'saving SVM as "shoes_svm_' + str(SZ) + '.dat"...'
  model.save('out/shoes_svm_' + str(SZ) + '.dat')
  
  print 'training RTrees...'
  model = RTrees()
  model.train(samples_train, labels_train)
  vis = evaluate_model(model, shoes_test, samples_test, labels_test)
  cv2.imwrite('out/RTrees_test_' + str(SZ) + '.jpg', vis)
  print 'saving RTrees as "shoes_rtrees_' + str(SZ) + '.dat"...'
  model.save('out/shoes_rtrees_' + str(SZ) + '.dat')
  
  