"""
# -*- coding: utf-8 -*-
-----------------------------------------------------------------------------------
# Author: Nguyen Mau Dung
# DoC: 2020.06.10
# email: nguyenmaudung93.kstn@gmail.com
# project repo: https://github.com/maudzung/TTNet-Realtime-for-Table-Tennis-Pytorch
-----------------------------------------------------------------------------------
# Description: This script for transformations of images, segmentation, and ball positions
"""

import random

import cv2
import numpy as np


class Compose(object):
    def __init__(self, transforms, p=1.0):
        self.transforms = transforms
        self.p = p

    def __call__(self, imgs, ball_position_xy, seg_img):
        if random.random() <= self.p:
            for t in self.transforms:
                imgs, ball_position_xy, seg_img = t(imgs, ball_position_xy, seg_img)
        return imgs, ball_position_xy, seg_img


class Normalize():
    def __init__(self, mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), num_frames_sequence=9, p=1.0):
        self.p = p
        self.mean = np.repeat(np.array(mean).reshape(1, 1, 3), repeats=num_frames_sequence, axis=-1)
        self.std = np.repeat(np.array(std).reshape(1, 1, 3), repeats=num_frames_sequence, axis=-1)

    def __call__(self, imgs, ball_position_xy, seg_img):
        if random.random() < self.p:
            imgs = ((imgs / 255.) - self.mean) / self.std

        return imgs, ball_position_xy, seg_img


class Denormalize():
    def __init__(self, mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), p=1.0):
        self.p = p
        self.mean = np.array(mean).reshape(1, 1, 3)
        self.std = np.array(std).reshape(1, 1, 3)

    def __call__(self, img):
        img = (img * self.std + self.mean) * 255.
        img = img.astype(np.uint8)

        return img


class Resize(object):
    def __init__(self, new_size, p=0.5, interpolation=cv2.INTER_LINEAR):
        self.new_size = new_size
        self.p = p
        self.interpolation = interpolation

    def __call__(self, imgs, ball_position_xy, seg_img):
        if random.random() <= self.p:
            h, w, c = imgs.shape
            # Resize a sequence of images
            imgs = cv2.resize(imgs, self.new_size, interpolation=self.interpolation)
            # Dont need to resize seg_img
            # Adjust ball position
            w_ratio = w / self.new_size[0]
            h_ratio = h / self.new_size[1]
            ball_position_xy = np.array([ball_position_xy[0] / w_ratio, ball_position_xy[1] / h_ratio])

        return imgs, ball_position_xy, seg_img


class Random_Crop(object):
    def __init__(self, max_reduction_percent=0.15, p=0.5, interpolation=cv2.INTER_LINEAR):
        self.max_reduction_percent = max_reduction_percent
        self.p = p
        self.interpolation = interpolation

    def __call__(self, imgs, ball_position_xy, seg_img):
        # imgs are before resizing
        if random.random() <= self.p:
            h, w, c = imgs.shape
            # Calculate min_x, max_x, min_y, max_y
            remain_percent = random.uniform(1. - self.max_reduction_percent, 1.)
            new_w = remain_percent * w
            min_x = int(random.uniform(0, w - new_w))
            max_x = int(min_x + new_w)
            w_ratio = w / new_w

            new_h = remain_percent * h
            min_y = int(random.uniform(0, h - new_h))
            max_y = int(new_h + min_y)
            h_ratio = h / new_h
            # crop a sequence of images
            imgs = imgs[min_y:max_y, min_x:max_x, :]
            imgs = cv2.resize(imgs, (w, h), interpolation=self.interpolation)
            # crop seg_img
            seg_img_h, seg_img_w, _ = seg_img.shape
            # 1. Resize to original
            if (seg_img_h != h) or (seg_img_w != w):
                seg_img = cv2.resize(seg_img, (w, h), interpolation=self.interpolation)
            # 2. Crop
            seg_img = seg_img[min_y:max_y, min_x:max_x, :]
            # 3. Resize to (128, 320, 3)
            seg_img = cv2.resize(seg_img, (seg_img_w, seg_img_h), interpolation=self.interpolation)

            # Adjust ball position
            ball_position_xy = np.array([(ball_position_xy[0] - min_x) * w_ratio,
                                         (ball_position_xy[1] - min_y) * h_ratio])

        return imgs, ball_position_xy, seg_img


class Random_Rotate(object):
    def __init__(self, rotation_angle_limit=15, p=0.5):
        self.rotation_angle_limit = rotation_angle_limit
        self.p = p

    def __call__(self, imgs, ball_position_xy, seg_img):
        if random.random() <= self.p:
            random_angle = random.uniform(-self.rotation_angle_limit, self.rotation_angle_limit)
            # Rotate a sequence of imgs
            h, w, c = imgs.shape
            center = (int(w / 2), int(h / 2))
            rotate_matrix = cv2.getRotationMatrix2D(center, random_angle, 1.)
            imgs = cv2.warpAffine(imgs, rotate_matrix, (w, h), flags=cv2.INTER_LINEAR)

            # Adjust ball position, apply the same rotate_matrix for the sequential images
            ball_position_xy = rotate_matrix.dot(np.array([ball_position_xy[0], ball_position_xy[1], 1.]).T)

            # Rotate seg_img
            seg_h, seg_w, seg_c = seg_img.shape
            if (seg_h != h) or (seg_w != w):
                seg_center = (int(seg_w / 2), int(seg_h / 2))
                seg_rotate_matrix = cv2.getRotationMatrix2D(seg_center, random_angle, 1.)
            else:
                seg_rotate_matrix = rotate_matrix
            seg_img = cv2.warpAffine(seg_img, seg_rotate_matrix, (seg_w, seg_h), flags=cv2.INTER_LINEAR)

        return imgs, ball_position_xy, seg_img


class Random_HFlip(object):
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, imgs, ball_position_xy, seg_img):
        if random.random() <= self.p:
            h, w, c = imgs.shape
            # Horizontal flip a sequence of imgs
            imgs = cv2.flip(imgs, 1)
            # Horizontal flip seg_img
            seg_img = cv2.flip(seg_img, 1)

            # Adjust ball position: Same y, new x = w - x
            ball_position_xy[0] = w - ball_position_xy[0]

        return imgs, ball_position_xy, seg_img


import random
import numpy as np
import cv2

class Random_Ball_Mask:
    def __init__(self, mask_size=(20, 20), p=0.5, mask_type='mean'):
        """
        Args:
            mask_size (tuple): Height and width of the mask area (blackout area).
            p (float): Probability of applying the mask.
            mask_type (str): Type of mask ('zero', 'noise', 'mean').
        """
        self.mask_size = mask_size
        self.p = p
        self.mask_type = mask_type

    def __call__(self, imgs, ball_position_xy, seg_img):
        """
        Args:
            imgs : Numpy array of shape [H, W, num_frames].
            ball_position_xy (numpy): (x, y) ball position for the labeled frame.
            seg_img: Corresponding segmentation mask.

        Returns:
            Tuple containing:
                - masked_imgs: Numpy array with masked frames.
                - ball_position_xy: Updated ball position.
                - seg_img: Unmodified segmentation image.
        """
        H, W, num_frames = imgs.shape  # Extract shape from stacked array

        # Ensure the mask size is valid
        mask_h = random.randint(max(1, self.mask_size[0] - 10), self.mask_size[0] + 10)
        mask_w = random.randint(max(1, self.mask_size[1] - 10), self.mask_size[1] + 10)

        # Iterate over all frames and apply masking with some probability
        for i in range(num_frames):
            if random.random() <= self.p:
                if i == num_frames - 1:
                    # Use the given ball position for the last frame
                    x, y = int(ball_position_xy[0]), int(ball_position_xy[1])
                else:
                    # Apply mask at a random position for non-labeled frames
                    x = random.randint(0, W - mask_w)
                    y = random.randint(0, H - mask_h)

                # Ensure the mask is within the image boundaries
                top = max(0, min(H - mask_h, y - mask_h // 2))
                left = max(0, min(W - mask_w, x - mask_w // 2))

                # Check if the selected region has valid pixels
                region = imgs[top:top + mask_h, left:left + mask_w, i]
                if region.size == 0:
                    print(f"Warning: Empty slice for frame {i}. Skipping mask.")
                    continue

                # Apply the chosen mask type
                if self.mask_type == 'zero':
                    imgs[top:top + mask_h, left:left + mask_w, i] = 0

                elif self.mask_type == 'noise':
                    noise = np.random.randn(mask_h, mask_w) * 255  # Generate noise
                    imgs[top:top + mask_h, left:left + mask_w, i] = noise.clip(0, 255)

                elif self.mask_type == 'mean':
                    mean_value = np.nanmean(region)  # Handle empty slices safely
                    noise = np.random.randn(mask_h, mask_w) * 10  # Small noise
                    imgs[top:top + mask_h, left:left + mask_w, i] = (mean_value + noise).clip(0, 255)

        return imgs, ball_position_xy, seg_img
