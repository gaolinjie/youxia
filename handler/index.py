#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2016 youxia

import uuid
import hashlib
from PIL import Image
import StringIO
import time
import json
import re
import urllib2
import tornado.web
import lib.jsonp
import pprint
import math
import datetime
import os
import requests
import MySQLdb
import helper

from base import *
from lib.sendmail import send
from lib.variables import *
from lib.variables import gen_random
from lib.xss import XssCleaner
from lib.utils import find_mentions
from lib.reddit import hot
from lib.utils import pretty_date
from lib.dateencoder import DateEncoder
from lib.utils import getJsonKeyValue

from lib.mobile import is_mobile_browser
from lib.mobile import is_weixin_browser

from qiniu import Auth
from qiniu import BucketManager
from qiniu import put_data

import xml.etree.ElementTree as ET
import commands

access_key = "FyIIPvo4crjBvyQas_Y50Nsob1Yz3QUZuKCTgru8"
secret_key = "RUeH0GpomE2vymovye58aevY9_FrGhbfpcGWWsQI"
q = Auth(access_key, secret_key)
bucket = BucketManager(q)


class IndexHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        template_variables["page_name"] = "App--index"

        p = int(self.get_argument("p", "1"))

        all_posts = self.item_model.get_all_posts(current_page = p)
        template_variables["all_posts"] = all_posts
        

        if(user_info):
            print 'ddd'
        else:
            print 'dasfafafasd'
            template_variables["sign_in_up"] = self.get_argument("s", "") 
            link = self.get_argument("link", "")
            if link!="":
                template_variables["link"] =  link
            link2 = self.get_argument("link2", "")
            if link2!="":
                template_variables["link2"] = link2 
            invite = self.get_argument("i", "")
            if invite!="":
                template_variables["invite"] = invite
            else:
                template_variables["invite"] = None
            error = self.get_argument("e", "")
            if error!="":
                template_variables["error"] = error
            else:
                template_variables["error"] = None
        self.render(self.template_path+"index.html", **template_variables)

class ReviewsHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        p = int(self.get_argument("p", "1"))

        all_cars1 = self.car_data_model.get_car_models_by_sort("热门车", current_page = p)
        template_variables["all_cars1"] = all_cars1
       
        self.render(self.template_path+"review.html", **template_variables)

class BbsHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        p = int(self.get_argument("p", "1"))
       
        self.render(self.template_path+"bbs.html", **template_variables)

class TagHandler(BaseHandler):
    def get(self, tag_name, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        p = int(self.get_argument("p", "1"))
       
        self.render(self.template_path+"tag.html", **template_variables)

class GetTagsHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["user_info"] = user_info
        allTags = self.tag_model.get_all_tags2()
        print allTags
        allTagJson = []
        for tag in allTags:
            allTagJson.append(tag.name)

        self.write(json.dumps(allTagJson))

class PostHandler(BaseHandler):
    def get(self, post_id, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        p = int(self.get_argument("p", "1"))
        template_variables["page_name"] = "App--discussion"

        if user_info:
            post = self.item_model.get_post_by_post_id_with_user(post_id, user_info.uid)
        else:
            post = self.item_model.get_post_by_post_id(post_id)
        template_variables["post"] = post
        #template_variables["tags"] = self.post_tag_model.get_post_all_tags(post_id)
        print "@@@"+post.content

        

        self.render(self.template_path+"post.html", **template_variables)

class NewHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        self.render(self.template_path+"new.html", **template_variables)

    @tornado.web.authenticated
    def post(self, template_variables = {}):
        user_info = self.current_user
        template_variables = {}

        post_type = self.get_argument('action', "save")

        post_info = {}
        data = json.loads(self.request.body)

        post_info = getJsonKeyValue(data, post_info, "title")
        post_info = getJsonKeyValue(data, post_info, "content")

        post_info["author_id"] = self.current_user["uid"]
        post_info["updated"] = time.strftime('%Y-%m-%d %H:%M:%S')
        post_info["created"] = time.strftime('%Y-%m-%d %H:%M:%S')

        last_post_id = self.item_model.get_max_post_id()
        if last_post_id:
            post_id = last_post_id + 1
        else:
            post_id = 1
        post_info["post_id"] = post_id
        post_info["first_type"] = "post"

        item_id = self.item_model.add_new_item(post_info)
        if item_id:
            success = 0
            message = "成功新建帖子"
            redirect = "/post/"+str(post_id)
        else:
            success = -1
            message = "新建帖子失败"
            redirect = ""

        self.write(lib.jsonp.print_JSON({
            "success": success,
            "message": message,
            "redirect": redirect
        }))

        '''
        # process tags
        tagStr = data["tags"]
        print tagStr
        if tagStr:
            tagNames = tagStr.split(',') 
            for tagName in tagNames:  
                tag = self.tag_model.get_tag_by_tag_name(tagName)
                if tag:
                    self.post_tag_model.add_new_post_tag({"post_id": post_id, "tag_id": tag.id})
                    self.tag_model.update_tag_by_tag_id(tag.id, {"post_num": tag.post_num+1})
        '''

        


class UploadImageHandler(BaseHandler):
    def post(self, template_variables = {}):
        template_variables = {}
        # validate the fields
        if("files" in self.request.files):            
            file_name = "%s" % uuid.uuid1()
            file_raw = self.request.files["files"][0]["body"]
            file_buffer = StringIO.StringIO(file_raw)
            file = Image.open(file_buffer)

            usr_home = os.path.expanduser('~')
            file.save(usr_home+"/%s.png" % file_name, "PNG")  

            uptoken = q.upload_token("yx-img", "%s.png" % file_name)
            data=open(usr_home+"/%s.png" % file_name)
            ret, info = put_data(uptoken, "%s.png" % file_name, data)
 
            os.remove(usr_home+"/%s.png" % file_name)

            file_name = "http://objdsnsh2.bkt.clouddn.com/"+file_name+".png"
            print file_name

            self.write(lib.jsonp.print_JSON({
                    "files": [
                        {
                            "name": file_name,
                        }]
            }))
class ReplyHandler(BaseHandler):
    def get(self, post_id, template_variables = {}):
        print 'fdsafsadf'
        user_info = self.current_user
        p = int(self.get_argument("page", "1"))

        if user_info:
            all_replys = self.item_model.get_post_all_replys_with_user_sort_by_created(post_id, user_info.uid, current_page = p)
        else:
            all_replys = self.item_model.get_post_all_replys_sort_by_created(post_id, current_page = p)
        
        '''
        print 'cccccc@@@@@@@@@@@@@@@@@@@'
        print all_replys
        print 'ddddd'
        for reply in all_replys['list']:
            reply['reply_replys'] = self.reply_model.get_reply_all_replys_sort_by_created(reply.id)
        print 'eeeee'
        '''
        replys_json = json.dumps(all_replys, cls=DateEncoder)
        print replys_json
        self.write(replys_json)

    @tornado.web.authenticated
    def post(self, post_id, template_variables = {}):
        user_info = self.current_user

        data = json.loads(self.request.body)
        content = data["content"]
        second_type = data["second_type"]
        reply_to = data["reply_to"]

        if(user_info):
            # update post
            post_item = self.item_model.get_post_by_post_id(post_id)
            self.item_model.update_item_by_id(post_item.id, {
                "reply_num": post_item.reply_num+1, 
                "last_reply_user": user_info.username,
                "last_reply_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                "updated": time.strftime('%Y-%m-%d %H:%M:%S'),
            })

            # update reply_item
            if (second_type == 'to_reply'):
                reply_item = self.item_model.get_item_by_id(reply_to)
                self.item_model.update_item_by_id(reply_item.id, {
                    "reply_num": reply_item.reply_num+1,
                    "reply_users": (reply_item.reply_users if reply_item.reply_users else '') + user_info.username + ',',  
                    "last_reply_user": user_info.username,
                    "last_reply_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "updated": time.strftime('%Y-%m-%d %H:%M:%S'),
                })


            reply_info = {
                "author_id": user_info["uid"],
                "post_id": post_id,
                "content": content,
                "first_type": "reply",
                "second_type": second_type,
                "reply_to": reply_to,
                "created": time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            reply_id = self.item_model.add_new_item(reply_info)

            self.write(lib.jsonp.print_JSON({
                    "success": 1,
                    "message": "successed",
                    "reply_id": reply_id
            }))
        else:
            self.write(lib.jsonp.print_JSON({
                    "success": 0,
                    "message": "failed",
            }))

class LikeHandler(BaseHandler):
    def get(self, item_id, template_variables = {}):
        user_info = self.current_user

        if(user_info):
            like = self.item_model.get_like_by_author_and_item_id(user_info.uid, item_id)
            if not like:
                item = self.item_model.get_item_by_id(item_id)
                self.item_model.update_item_by_id(item_id, {
                    "like_num": item.like_num+1,
                    "like_users": (item.like_users if item.like_users else '') + user_info.username + ',',  })
                self.item_model.add_new_item({
                    "post_id": item.post_id,
                    "first_type": "like",
                    "second_type": item.first_type,
                    "reply_to": item_id,
                    "author_id": user_info.uid,
                    "created": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            self.write(lib.jsonp.print_JSON({
                    "success": 1,
                    "message": "successed",
                }))
        else:
            self.write(lib.jsonp.print_JSON({
                    "success": 0,
                    "message": "successed",
                }))

class TagsHandler(BaseHandler):
    def get(self, template_variables = {}):
        user_info = self.current_user
        template_variables["static_path"] = self.static_path
        template_variables["user_info"] = user_info
        p = int(self.get_argument("p", "1"))
       
        self.render(self.template_path+"tags.html", **template_variables)