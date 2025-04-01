# coding=utf-8
#
# Copyright 2016 timercrack
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import redis
import ujson as json

import pytz
import time
import datetime
import logging
from collections import defaultdict
from django.utils import timezone
from croniter import croniter
import asyncio
from abc import abstractmethod, ABCMeta
import aioredis

from trader.utils.func_container import CallbackFunctionContainer
from trader.utils.read_config import config

logger = logging.getLogger('BaseModule')


class BaseModule(CallbackFunctionContainer, metaclass=ABCMeta):
    """
    交易策略的基础抽象类，提供事件驱动架构和消息处理框架
    
    主要功能:
    1. 异步事件循环管理
    2. Redis 发布/订阅通信
    3. 定时任务和消息回调注册
    4. 生命周期管理
    """
    def __init__(self):
        """初始化基础模块，设置事件循环和Redis连接"""
        super().__init__()
        # 创建独立的事件循环
        self.io_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.io_loop)
        # 创建异步Redis客户端
        self.redis_client = aioredis.from_url(
            f"redis://{config.get('REDIS', 'host', fallback='localhost')}:"
            f"{config.getint('REDIS', 'port', fallback=6379)}/{config.getint('REDIS', 'db', fallback=0)}",
            decode_responses=True)
        # 创建同步Redis客户端（用于简单操作）
        self.raw_redis = redis.StrictRedis(host=config.get('REDIS', 'host', fallback='localhost'),
                                           port=config.getint('REDIS', 'port', fallback=6379),
                                           db=config.getint('REDIS', 'db', fallback=0), decode_responses=True)
        # 创建Redis订阅客户端
        self.sub_client = self.redis_client.pubsub()
        self.initialized = False
        self.sub_tasks = list()
        self.sub_channels = list()
        # 消息路由表：将频道映射到回调函数
        self.channel_router = dict()
        # 定时任务路由表：将cron表达式映射到回调函数
        self.crontab_router = defaultdict(dict)
        self.datetime = None
        self.time = None
        self.loop_time = None

    def _register_callback(self):
        """注册所有回调函数，包括定时任务和消息回调"""
        self.datetime = timezone.localtime()
        self.time = time.time()
        self.loop_time = self.io_loop.time()
        for fun_name, args in self.callback_fun_args.items():
            if 'crontab' in args:
                # 注册定时任务回调
                key = args['crontab']
                self.crontab_router[key]['func'] = getattr(self, fun_name)
                self.crontab_router[key]['iter'] = croniter(args['crontab'], self.datetime)
                self.crontab_router[key]['handle'] = None
            elif 'channel' in args:
                # 注册消息回调
                self.channel_router[args['channel']] = getattr(self, fun_name)

    def _get_next(self, key):
        """计算下一次定时任务的执行时间"""
        return self.loop_time + (self.crontab_router[key]['iter'].get_next() - self.time)

    def _call_next(self, key):
        """执行定时任务并安排下一次执行"""
        if self.crontab_router[key]['handle'] is not None:
            self.crontab_router[key]['handle'].cancel()
        # 安排下一次执行
        self.crontab_router[key]['handle'] = self.io_loop.call_at(self._get_next(key), self._call_next, key)
        # 执行当前任务
        self.io_loop.create_task(self.crontab_router[key]['func']())

    async def install(self):
        """安装模块：注册回调、订阅消息、启动定时任务"""
        try:
            self._register_callback()
            # 订阅所有配置的频道
            await self.sub_client.psubscribe(*self.channel_router.keys())
            # 启动消息监听器
            asyncio.run_coroutine_threadsafe(self._msg_reader(), self.io_loop)
            # self.io_loop.create_task(self._msg_reader())
            # 启动所有定时任务
            for key, cron_dict in self.crontab_router.items():
                if cron_dict['handle'] is not None:
                    cron_dict['handle'].cancel()
                cron_dict['handle'] = self.io_loop.call_at(self._get_next(key), self._call_next, key)
            self.initialized = True
            logger.debug('%s plugin installed', type(self).__name__)
        except Exception as e:
            logger.error('%s plugin install failed: %s', type(self).__name__, repr(e), exc_info=True)

    async def uninstall(self):
        """卸载模块：取消订阅、停止定时任务、释放资源"""
        try:
            # 取消所有订阅
            await self.sub_client.punsubscribe()
            # await asyncio.wait(self.sub_tasks, loop=self.io_loop)
            self.sub_tasks.clear()
            await self.sub_client.close()
            # 取消所有定时任务
            for key, cron_dict in self.crontab_router.items():
                if self.crontab_router[key]['handle'] is not None:
                    self.crontab_router[key]['handle'].cancel()
                    self.crontab_router[key]['handle'] = None
            self.initialized = False
            logger.debug('%s plugin uninstalled', type(self).__name__)
        except Exception as e:
            logger.error('%s plugin uninstall failed: %s', type(self).__name__, repr(e), exc_info=True)

    async def _msg_reader(self):
        """消息监听器：接收Redis消息并分发到对应的回调函数"""
        # {'type': 'pmessage', 'pattern': 'channel:*', 'channel': 'channel:1', 'data': 'Hello'}
        async for msg in self.sub_client.listen():
            if msg['type'] == 'pmessage':
                channel = msg['channel']
                pattern = msg['pattern']
                data = json.loads(msg['data'])
                # logger.debug("%s channel[%s] Got Message:%s", type(self).__name__, channel, msg)
                # 异步执行对应的回调函数
                self.io_loop.create_task(self.channel_router[pattern](channel, data))
            elif msg['type'] == 'punsubscribe':
                break
        logger.debug('%s quit _msg_reader!', type(self).__name__)

    async def start(self):
        """启动模块"""
        await self.install()

    async def stop(self):
        """停止模块"""
        await self.uninstall()

    def run(self):
        """运行模块的主循环"""
        try:
            self.io_loop.create_task(self.start())
            self.io_loop.run_forever()
        except KeyboardInterrupt:
            self.io_loop.run_until_complete(self.stop())
        except Exception as ee:
            logger.error('发生错误: %s', repr(ee), exc_info=True)
            self.io_loop.run_until_complete(self.stop())
        finally:
            logger.debug('程序已退出')
