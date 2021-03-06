import sys
import json
import torch
import numpy as np
import argparse
import torchvision.transforms as transforms
import cv2
from DRL.ddpg import decode
from utils.util import *
from PIL import Image
from torchvision import transforms, utils
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

aug = transforms.Compose(
            [transforms.ToPILImage(),
             transforms.RandomHorizontalFlip(),
             ])

width = 128
convas_area = width * width

img_train = []
img_test = []
train_num = 0
test_num = 0

class Paint:
    def __init__(self, batch_size, max_step):
        self.batch_size = batch_size
        self.max_step = max_step
        self.action_space = (21)
        self.observation_space = (self.batch_size, width, width, 7)
        self.test = False
        
    def load_data(self):
        global train_num, test_num
        imgs = np.load('./data/kanji.npz')['arr_0']
        for i in range(60000):
            img = cv2.resize(imgs[i,:,:], (width, width), interpolation=cv2.INTER_LINEAR)
            img = np.stack((img,)*3, axis=-1)
            if i > 1000:
                train_num += 1
                img_train.append(img)
            else:
                test_num += 1
                img_test.append(img)
        del imgs
        print('finish loading data, {} training images, {} testing images'.format(str(train_num), str(test_num)))
        
    def pre_data(self, id, test):
        if test:
            img = img_test[id]
        else:
            img = img_train[id]
        if not test:
            img = aug(img)
        img = np.asarray(img)
        return np.transpose(img, (2, 0, 1))
    
    def reset(self, test=False, begin_num=False):
        self.test = test
        self.imgid = [0] * self.batch_size
        self.gt = torch.zeros([self.batch_size, 3, width, width], dtype=torch.uint8).to(device)
        for i in range(self.batch_size):
            if test:
                id = (i + begin_num)  % test_num
            else:
                id = np.random.randint(train_num)
            self.imgid[i] = id
            self.gt[i] = torch.tensor(self.pre_data(id, test))
        self.tot_reward = ((self.gt.float() / 255) ** 2).mean(1).mean(1).mean(1)
        self.stepnum = 0
        self.canvas = torch.zeros([self.batch_size, 3, width, width], dtype=torch.uint8).to(device)
        self.lastdis = self.ini_dis = self.cal_dis()
        self.prev_action = None
        return self.observation()
    
    def observation(self):
        # canvas B * 3 * width * width
        # gt B * 3 * width * width
        # T B * 1 * width * width
        ob = []
        T = torch.ones([self.batch_size, 1, width, width], dtype=torch.uint8) * self.stepnum
        return torch.cat((self.canvas, self.gt, T.to(device)), 1) # canvas, img, T

    def cal_trans(self, s, t):
        return (s.transpose(0, 3) * t).transpose(0, 3)
    
    def step(self, action):
        #if torch.is_tensor(self.prev_action):
            # strokeの間を繋ぐ
            #new_action = [
            #    self.prev_action[:,4:6],
            #    self.prev_action[:,4:6],
            #    action[:,:2],
            #    self.prev_action[:,7:8],
            #    action[:,6:7],
            #    action[:,8:13]
            #]
            #connect_action = torch.cat(new_action, dim=1)
            #self.canvas = (decode(connect_action, self.canvas.float() / 255) * 255).byte()
        self.canvas = (decode(action, self.canvas.float() / 255) * 255).byte()
        self.stepnum += 1
        self.prev_action = action
        ob = self.observation()
        done = (self.stepnum == self.max_step)
        reward = self.cal_reward() # np.array([0.] * self.batch_size)
        return ob.detach(), reward, np.array([done] * self.batch_size), None

    def cal_dis(self):
        return (((self.canvas.float() - self.gt.float()) / 255) ** 2).mean(1).mean(1).mean(1)
    
    def cal_reward(self):
        dis = self.cal_dis()
        reward = (self.lastdis - dis) / (self.ini_dis + 1e-8) - self.stepnum / 32
        self.lastdis = dis
        return to_numpy(reward)
