__author__ = 'robdefeo'
import cv2
from improc.color import Matrix_scikit_kmeans
from improc.crop import AutoCrop


def grey(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def autocrop(img):

    (
        matrix,
        cluster_centers_,
        labels,
        background_label
    ) = Matrix_scikit_kmeans(img, 5)


    (
        img_autocrop,
        x,
        y,
        width,
        height
    ) = AutoCrop(img, labels, background_label)

    return img_autocrop

def resize(img, size):
    return cv2.resize(img, size)

def add_border(img, border_size=15, color_value=255):
    return cv2.copyMakeBorder(
        img,
        border_size, border_size, border_size, border_size,
        cv2.BORDER_CONSTANT,
        value=color_value
    )