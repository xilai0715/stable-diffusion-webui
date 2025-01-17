#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/8/21 3:53 PM
# @Author  : wangdongming
# @Site    :
# @File    : gen_fusion_img.py
# @Software: Hifive
import random
import time
import typing
import modules
import cv2
import numpy as np
import insightface
import onnxruntime
import os
import math

from modules import shared, scripts
from loguru import logger
from PIL import ImageOps, Image
from handlers.txt2img import Txt2ImgTask, Txt2ImgTaskHandler
from worker.task import TaskType, TaskProgress, Task, TaskStatus
from modules.processing import StableDiffusionProcessingImg2Img, process_images, Processed, fix_seed
from handlers.utils import init_script_args, get_selectable_script, init_default_script_args, \
    load_sd_model_weights, save_processed_images, get_tmp_local_path, get_model_local_path
from copy import deepcopy
from typing import List, Union, Dict, Set, Tuple
import requests
from retry import retry
from io import BytesIO
import tempfile
from handlers.rmf.inference import rmf_seg

from timeout_decorator import timeout
from filestorage.__init__ import push_local_path
import datetime

# conversion_action={"线稿":'line',"黑白":'black_white',"色块":'color','草图':'sketch','蜡笔':'crayon'}

# rendition_style={"彩铅":'color_pencil',"浮世绘":'ukiyo',"山水画":'landscape',"极简水彩":'min_watercolor',"炫彩":'dazzle_color',"油画":'oil_paint'}
# NOTE: 2023.10.30
"""
保持-{"山水画":'landscape',,"炫彩":'dazzle_color',"油画":'oil_paint'}
调整-{'原极简水彩': 'min_watercolor', '原彩铅风': 'color_pencil', '原浮世绘风': 'ukiyo'}；
新增-{'国风插画': 'chinese_illustration', '凤冠霞帔风格': 'chinese_wedding', '汉服服饰风格': 'chinese_hanfu',
'婚纱服饰风格': 'wedding', '旗袍服饰风格': 'qipao', '西装服饰风格': 'suits', '简约头像': 'simple_headshots ', 'JK服饰风格': 'jk',
'国风彩墨画': 'chinese_colorful', '艺术插画': 'art_illustration', '趣怪画': 'spoof', '插画头像': 'illustration_headshots'}
"""
# NOTE: 2023.11.16
"""
调整-{'原极简水彩': 'min_watercolor','国风插画': 'chinese_illustration','简约头像': 'simple_headshots ', 'JK服饰风格': 'jk',"油画":'oil_paint'}
"""


def size_control(width, height):
    # 尺寸检查，最大1024*1024
    if width * height > 1024 * 1024:
        rate = (1024 * 1024) / (width * height)
        width = int(width * rate)
        height = int(height * rate)
    return width, height


def get_multidiffusion_args():
    onepress_multidiffusion_args = {'Tiled-Diffusion': {'args':
                                                            [{'batch_size': 1, 'causal_layers': False,
                                                              'control_tensor_cpu': False, 'controls':
                                                                  [{'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4},
                                                                   {'blend_mode': 'Background', 'enable': False,
                                                                    'feather_ratio': 0.2, 'h': 0.2, 'neg_prompt': '',
                                                                    'prompt': '', 'seed': -1, 'w': 0.2, 'x': 0.4,
                                                                    'y': 0.4}],

                                                              'draw_background': False, 'enable_bbox_control': False,
                                                              'enabled': True, 'image_height': 1024,
                                                              'image_width': 1024, 'keep_input_size': True,

                                                              'method': 'Mixture of Diffusers', 'noise_inverse': True,
                                                              'noise_inverse_renoise_kernel': 64,
                                                              'noise_inverse_renoise_strength': 0,

                                                              'noise_inverse_retouch': 1, 'noise_inverse_steps': 35,
                                                              'overlap': 48, 'overwrite_image_size': False,
                                                              'overwrite_size': False, 'scale_factor': 2,

                                                              'tile_height': 96, 'tile_width': 96,
                                                              'upscaler': 'None'}]}}

    return onepress_multidiffusion_args


def get_llul_args():
    onepress_llul_args = {'LLuL': {'args': [{'apply_to': ['OUT'], 'down': 'Pooling Max', 'down_aa': False,
                                             'enabled': True, 'force_float': False, 'intp': 'Lerp', 'layers':
                                                 'OUT', 'max_steps': 0, 'multiply': 1, 'start_steps': 1,
                                             'understand': False,

                                             'up': 'Bilinear', 'up_aa': False, 'weight': 0.15, 'x': 128, 'y': 128}]}}
    return onepress_llul_args


def get_cn_args():
    onepress_cn_args = {
        "control_mode": "Balanced",
        "enabled": True,
        "guess_mode": False,
        "guidance_end": 1,
        "guidance_start": 0,
        "image": {"image": None, "mask": None},
        "invert_image": False,
        "isShowModel": True,
        "low_vram": False,
        "model": None,
        "module": None,
        "pixel_perfect": True,
        "processor_res": 512,
        "resize_mode": "Scale to Fit (Inner Fit)",
        "tempMask": None,
        "threshold_a": 1,
        "threshold_b": -1,
        "weight": 1
    }

    return onepress_cn_args


def change_cn_args(module, model, weight=1, image=None, guidance_start=0, guidance_end=1):
    cn_args = get_cn_args()
    cn_args['enabled'] = True
    cn_args['module'] = module  # 预处理器
    cn_args['model'] = model  # 模型
    cn_args['image']['image'] = image  # 图片入参
    cn_args['weight'] = weight  # 权重
    cn_args['guidance_start'] = guidance_start  # 引导初始值
    cn_args['guidance_end'] = guidance_end  # 引导结束值
    cn_args['threshold_a'] = -1
    cn_args['threshold_b'] = -1

    return cn_args


def get_txt2img_args(prompt, width, height):
    # 内置万能提示词
    prompt = 'masterpiece, (highres 1.2), (ultra-detailed 1.2),' + prompt
    negative_prompt = '(worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality,M,nsfw,'
    # 做尺寸控制
    width, height = size_control(width, height)
    onepress_txt2img_args = {'prompt': prompt, 'negative_prompt': negative_prompt,
                             'sampler_name': 'DPM++ 2M SDE Karras',
                             'steps': 25,
                             'cfg_scale': 7,
                             'denoising_strength': 0.7,
                             'width': width, 'height': height, 'n_iter': 1, 'batch_size': 1}
    return onepress_txt2img_args


def get_img2img_args(prompt, width, height, init_img):
    onepress_img2img_args = get_txt2img_args(prompt, width, height)
    onepress_img2img_args['denoising_strength'] = 0.75  # 蜡笔画
    onepress_img2img_args['init_img'] = init_img
    onepress_img2img_args['sketch'] = ''
    onepress_img2img_args['init_img_with_mask'] = {'image': '', 'mask': ''}
    return onepress_img2img_args


class OnePressTaskType(Txt2ImgTask):
    Conversion = 1  # 图片上色：
    Rendition = 2  # 风格转换
    ImgToGif = 3  # 静态图片转动图
    ArtWord = 4  # 艺术字
    LaternFair = 5  # 灯会变身
    SegImg = 6 # 抠图
    KidDrawring=7 # 儿童画变灯笼

class ConversionTask(Txt2ImgTask):
    def __init__(self,
                 base_model_path: str,  # 模型路径
                 model_hash: str,  # 模型hash值
                 image: str,  # 图片路径
                 action: str,  # 转换方式
                 prompt: str,  # 图片的正向提示词
                 full_canny: bool = False,  # 图片细化
                 part_canny: bool = False,  # 区域细化
                 ):
        self.base_model_path = base_model_path
        self.model_hash = model_hash
        self.image = image
        self.action = action
        self.prompt = prompt
        self.full_canny = full_canny
        self.part_canny = part_canny

    @classmethod
    def exec_task(cls, task: Task):
        t = ConversionTask(
            task['base_model_path'],
            task['model_hash'],
            task['image'],
            task['action'],
            task['prompt'],
            task.get('full_canny', False),
            task.get('part_canny', False), )
        is_img2img = False
        full_canny = t.full_canny
        part_canny = t.part_canny
        full_task = deepcopy(task)
        full_task['alwayson_scripts'] = {'ControlNet': {'args': []}}

        """
        1.线稿-Linert，处理器-lineart_realistic（文生图）
        2.色块-tile，处理器-tile_colorfix+sharp（文生图）
        3.草图-canny，预处理器-canny（文生图）
        4.蜡笔-scrible，预处理器-scribble_pidinet（图生图模式）
        """
        # conversion_actiob={"线稿":'line',"黑白":'black_white',"色块":'color','草图':'sketch','蜡笔':'crayon'}
        if t.action == 'crayon':
            is_img2img = True
            init_img_inpaint = get_tmp_local_path(t.image)
            image = Image.open(init_img_inpaint).convert('RGB')
            full_task.update(get_img2img_args(
                t.prompt, image.width, image.height, t.image))
            cn_args = change_cn_args(
                'scribble_pidinet', 'control_v11p_sd15_scribble [d4ba51ff]', 1, t.image, 0, 1)
            full_task['alwayson_scripts']['ControlNet']['args'].append(cn_args)
        else:
            init_img_inpaint = get_tmp_local_path(t.image)
            image = Image.open(init_img_inpaint).convert('RGB')
            full_task.update(get_txt2img_args(
                t.prompt, image.width, image.height))
            if t.action == 'line':  # 线稿
                cn_args = change_cn_args('invert (from white bg & black line)',
                                         'control_v11p_sd15_lineart [43d4be0d]', 1, t.image, 0, 1)
                full_task['alwayson_scripts']['ControlNet']['args'].append(
                    cn_args)
            elif t.action == 'black_white':  # 黑白
                cn_args_1 = change_cn_args(
                    'lineart_realistic', 'control_v11p_sd15_lineart [43d4be0d]', 0.6, t.image, 0, 1)
                cn_args_2 = change_cn_args(
                    'depth_zoe', 'diff_control_sd15_depth_fp16 [978ef0a1]', 0.4, t.image, 0, 1)
                full_task['alwayson_scripts']['ControlNet']['args'].append(
                    cn_args_1)
                full_task['alwayson_scripts']['ControlNet']['args'].append(
                    cn_args_2)
            elif t.action == 'sketch':  # 草图
                cn_args = change_cn_args(
                    'canny', 'control_v11p_sd15_canny [d14c016b]', 1, t.image, 0, 1)
                full_task['alwayson_scripts']['ControlNet']['args'].append(
                    cn_args)
            elif t.action == 'color':  # 色块
                cn_args = change_cn_args(
                    'tile_colorfix+sharp', 'control_v11f1e_sd15_tile [a371b31b]', 1, t.image, 0, 1)
                full_task['alwayson_scripts']['ControlNet']['args'].append(
                    cn_args)
            else:
                pass

        full_task['override_settings_texts'] = ["sd_vae:None"]
        return full_task, is_img2img, full_canny, part_canny


class RenditionTask(Txt2ImgTask):
    def __init__(self,
                 base_model_path: str,  # 模型路径
                 model_hash: str,  # 模型hash值
                 style: str,  # 转绘风格 color_pencil/ukiyo/landscape/  min_watercolor/dazzle_color/oil_paint
                 width: int,  # 宽
                 height: int,  # 高
                 prompt: str,  # 图片的正向提示词
                 image: str,  # 原图路径
                 init_img: str,  # 油画垫图
                 lora_models: typing.Sequence[str] = None,  # lora
                 roop: bool = False,  # 换脸
                 batch_size: int = 1,  # 结果数量
                 is_fast: bool = False  # 极速模式
                 ):
        self.base_model_path = base_model_path
        self.model_hash = model_hash
        self.loras = lora_models
        self.prompt = prompt
        self.width = width if width != 0 else 512
        self.height = height if height != 0 else 512
        self.style = style
        self.image = image
        self.init_img = init_img
        self.roop = roop
        self.batch_size = batch_size if batch_size != 0 else 1
        self.is_fast = is_fast

    @classmethod
    def exec_task(cls, task: Task):

        t = RenditionTask(
            task['base_model_path'],
            task['model_hash'],
            task['style'],
            task['width'],
            task['height'],
            task.get('prompt', ""),
            task.get('image', None),  # 图生图：极简水彩 炫彩 油画
            task.get('init_img', None),  # 风格垫图 油画判断
            task.get('lora_models', None),
            task.get('roop', False),
            task.get('batch_size', 1),
            task.get('is_fast', False))  # 极速模式

        extra_args = deepcopy(task['extra_args'])
        task.pop("extra_args")
        full_task = deepcopy(task)
        full_task.update(extra_args)
        full_task['batch_size'] = t.batch_size
        full_task['is_fast'] = t.is_fast
        # 图生图模式
        is_img2img = extra_args['rendition_is_img2img']
        if is_img2img:
            full_task['init_img'] = t.image
        # 更新 controlnet的图片
        if 'ControlNet' in full_task['alwayson_scripts']:
            length = len(full_task['alwayson_scripts']['ControlNet']['args'])
            for i in range(0, length):
                full_task['alwayson_scripts']['ControlNet']['args'][i]['image']['image'] = t.image

        # NOTE 如果是极速模式，就改动相应的采样器 提示词后面添加lora，采样步数 cfg ，lcm的lora加上(要判断是否是xl模型)
        if t.is_fast:
            if extra_args['is_xl']:
                full_task['lora_models'].append(
                    'sd-web/resources/LCM/lcm-lora-xl.safetensors')
                full_task['prompt'] += ',<lora:lcm-lora-xl:1.0>'
            else:
                full_task['lora_models'].append(
                    'sd-web/resources/LCM/lcm-lora-sd15.safetensors')
                full_task['prompt'] += ',<lora:lcm-lora-sd15:1.0>'
            full_task['steps'] = 8
            full_task['cfg_scale'] = 1.3
            full_task['sampler_name'] = 'LCM-Alpha'

        # Lora
        if full_task['lora_models'] == ['']:
            full_task['lora_models'] = None
        if full_task['embeddings'] == ['']:
            full_task['embeddings'] = None

        return full_task, is_img2img

    @classmethod
    def exec_roop(cls, source_img: Image.Image, target_img: Image.Image, ):

        def get_face(img_data: np.ndarray, providers, det_size=(640, 640)):
            models_dir = os.path.join(
                scripts.basedir(), "models" + os.path.sep + "roop" + os.path.sep + "buffalo_l")
            face_analyser = insightface.app.FaceAnalysis(
                name=models_dir, providers=providers)
            face_analyser.prepare(ctx_id=0, det_size=det_size)
            face = face_analyser.get(img_data)

            if len(face) == 0 and det_size[0] > 320 and det_size[1] > 320:
                det_size_half = (det_size[0] // 2, det_size[1] // 2)
                return get_face(img_data, providers, det_size=det_size_half)

            try:
                return sorted(face, key=lambda x: x.bbox[0])
            except IndexError:
                return None

        source_img = cv2.cvtColor(np.array(source_img), cv2.COLOR_RGB2BGR)
        target_img = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)

        # 获取人脸
        providers = onnxruntime.get_available_providers()
        source_face = get_face(source_img, providers)
        target_face = get_face(target_img, providers)
        if source_face is None or target_face is None:
            return target_img
        # 人脸对应：算出中心点，判别与目标点最近的一张脸的位置，进行交换
        source_point = []
        for _ in source_face:
            box = _.bbox.astype(np.int)
            source_point.append(((box[2] + box[0]) / 2, (box[3] + box[1]) / 2))

        # 交换人脸
        models_path = os.path.join(scripts.basedir(),
                                   "models" + os.path.sep + "roop" + os.path.sep + "inswapper_128.onnx")
        face_swapper = insightface.model_zoo.get_model(
            models_path, providers=providers)
        result = target_img
        for _ in target_face:
            box = _.bbox.astype(np.int)
            point = ((box[2] + box[0]) / 2, (box[3] + box[1]) / 2)
            dis = [math.sqrt((point[0] - k[0]) ** 2 + (point[1] - k[1]) ** 2)
                   for k in source_point]
            # 距离最近的人脸
            s_face = source_face[dis.index(min(dis))]
            result = face_swapper.get(result, _, s_face)
        result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

        # 人脸修复的过程
        original_image = result_image.copy()
        numpy_image = np.array(result_image)
        face_restorer = None
        for restorer in shared.face_restorers:
            if restorer.name() == 'GFPGAN':
                face_restorer = restorer
                break
        numpy_image = face_restorer.restore(numpy_image)
        restored_image = Image.fromarray(numpy_image)
        result_image = Image.blend(original_image, restored_image, 1)

        return result_image


class ImgtoGifTask(Txt2ImgTask):
    def __init__(self,
                 base_model_path: str,  # 模型路径
                 model_hash: str,  # 模型hash值
                 width: int,  # 宽
                 height: int,  # 高
                 prompt: str,  # 图片的正向提示词
                 image: str,  # 原图路径
                 lora_models: typing.Sequence[str] = None,  # lora
                 batch_size: int = 1  # 结果数量
                 ):
        self.base_model_path = base_model_path
        self.model_hash = model_hash
        self.loras = lora_models
        self.prompt = prompt
        self.width = width if width != 0 else 512
        self.height = height if height != 0 else 512
        self.image = image
        self.batch_size = batch_size if batch_size != 0 else 1

    @classmethod
    def exec_task(cls, task: Task):

        t = ImgtoGifTask(
            task['base_model_path'],
            task['model_hash'],
            task['width'],
            task['height'],
            task.get('prompt', ""),
            task.get('image', None),  # 图生图：极简水彩 炫彩 油画
            task.get('lora_models', None),
            task.get('batch_size', 1))
        extra_args = deepcopy(task['extra_args'])
        task.pop("extra_args")
        full_task = deepcopy(task)
        full_task.update(extra_args)
        # 图生图模式
        is_img2img = True
        if is_img2img:
            full_task['init_img'] = t.image
        # 更新 controlnet的图片
        if 'ControlNet' in full_task['alwayson_scripts']:
            length = len(full_task['alwayson_scripts']['ControlNet']['args'])
            for i in range(0, length):
                full_task['alwayson_scripts']['ControlNet']['args'][i]['image']['image'] = t.image
        # animatediff = {"args": [
        #     {'model': 'mm_sd_v15_v2.ckpt', 'enable': True, 'video_length': 8, 'fps': 8, 'loop_number': 0, 'closed_loop': 'R+P', 'batch_size': 16, 'stride': 1, 'overlap': -1, 'format': [
        #         'PNG'], 'interp': 'Off', 'interp_x': 10, 'video_source': None, 'video_path': '', 'latent_power': 1, 'latent_scale': 32, 'last_frame': None, 'latent_power_last': 1, 'latent_scale_last': 32, 'request_id': ''}
        # ]
        # }
        # full_task['alwayson_scripts']['animatediff'] = animatediff
        # Lora
        if full_task['lora_models'] == ['']:
            full_task['lora_models'] = None
        if full_task['embeddings'] == ['']:
            full_task['embeddings'] = None
        return full_task, is_img2img


class ArtWordTask(Txt2ImgTask):
    def __init__(self,
                 type: str,  # 功能类型
                 base_model_path: str,  # 模型路径
                 model_hash: str,  # 模型hash值
                 width: int,  # 宽
                 height: int,  # 高
                 prompt: str,  # 图片的正向提示词
                 image: str,  # 原图路径
                 denoising_strength: float = 0.7,
                 lora_models: typing.Sequence[str] = None,  # lora
                 batch_size: int = 1,  # 结果数量
                 roop: bool = False,  # 换脸
                 is_fast: bool = False  # 极速模式
                 ):
        self.type = type
        self.base_model_path = base_model_path
        self.model_hash = model_hash
        self.loras = lora_models
        self.prompt = prompt
        self.denoising_strength = denoising_strength
        self.width = width if width != 0 else 512
        self.height = height if height != 0 else 512
        self.image = image
        self.roop = roop
        self.batch_size = batch_size if batch_size != 0 else 1
        self.is_fast = is_fast

    @classmethod
    def exec_task(cls, task: Task):

        t = ArtWordTask(
            task['type'],  # 艺术字，文生图，图生图
            task['base_model_path'],
            task['model_hash'],
            task['width'],
            task['height'],
            task.get('prompt', ""),
            task.get('image', None),  # 图生图的底图，艺术字的垫图
            task.get('denoising_strength', 0.7),  # 图生图的重绘幅度，艺术字的控制强度
            task.get('lora_models', None),
            task.get('batch_size', 1),
            task.get('roop', False),  # 是否换脸
            task.get('is_fast', False))  # 极速模式

        extra_args = deepcopy(task['extra_args'])
        task.pop("extra_args")
        full_task = deepcopy(task)
        full_task.update(extra_args)
        full_task['batch_size'] = t.batch_size
        full_task['is_fast'] = t.is_fast

        # 艺术字：文生图+controlnet模型,強度控制control的权重
        if t.type == 'artword':
            if 'ControlNet' in full_task['alwayson_scripts']:
                length = len(full_task['alwayson_scripts']['ControlNet']['args'])
                for i in range(0, length):
                    full_task['alwayson_scripts']['ControlNet']['args'][i]['image']['image'] = t.image
                    full_task['alwayson_scripts']['ControlNet']['args'][i]['enabled'] = True
                full_task['alwayson_scripts']['ControlNet']['args'][0]['weight'] = t.denoising_strength
        # 图生图:强度控制重绘幅度
        is_img2img = False
        if t.type == 'img2img':
            is_img2img, full_task['init_img'] = True, t.image
            full_task['denoising_strength'] = t.denoising_strength
        # NOTE 如果是极速模式，就改动相应的采样器 提示词后面添加lora，采样步数 cfg ，lcm的lora加上(要判断是否是xl模型)
        if t.is_fast:
            if extra_args['is_xl']:
                full_task['lora_models'].append(
                    'sd-web/resources/LCM/lcm-lora-xl.safetensors')
                full_task['prompt'] += ',<lora:lcm-lora-xl:1.0>'
            else:
                full_task['lora_models'].append(
                    'sd-web/resources/LCM/lcm-lora-sd15.safetensors')
                full_task['prompt'] += ',<lora:lcm-lora-sd15:1.0>'
            full_task['steps'] = 8
            full_task['cfg_scale'] = 1.3
            full_task['sampler_name'] = 'LCM-Alpha'

        # Lora
        if full_task['lora_models'] == ['']:
            full_task['lora_models'] = None
        if full_task['embeddings'] == ['']:
            full_task['embeddings'] = None

        return full_task, is_img2img


class LaternFairTask(Txt2ImgTask):
    def __init__(self,
                 image: str,  # 功能类型
                 backgroud_image: str,
                 args: dict,  # 极速模式
                 rate_width: float = 2,
                 rate_height: float = 5,
                 border_size: int = 160,
                 resize_width: int = 0,
                 resize_height: int = 0,
                 background_image_vertical: str = None
                 ):
        self.image = image
        self.backgroud_image = backgroud_image
        self.args = args
        self.rate_width = rate_width
        self.rate_height = rate_height
        self.border_size = border_size
        self.resize_width = resize_width
        self.resize_height = resize_height
        self.background_image_vertical = background_image_vertical

    @classmethod
    def exec_task(cls, task: Task):
        t = LaternFairTask(
            task['image'],
            task['background_image'],
            task['args'],
            task.get("rate_width", 2),
            task.get("rate_height", 5),
            task.get("border_size", 160),
            task.get("resize_width", 0),
            task.get("resize_height", 0),
            task.get("background_image_vertical", None)
        )
        extra_args = deepcopy(task['args'])
        full_task = deepcopy(task)
        full_task.pop("args")
        full_task.pop("background_image")
        full_task.pop("image")
        full_task.update(extra_args)
        # 分割一下backgroud_image
        if t.background_image_vertical is None:
            images_background = t.backgroud_image.split(',')
            backgroud_image_H = images_background[0]
            if len(images_background) > 1:
                backgroud_image_V = random.choice(images_background[1:])
            else:
                backgroud_image_V = None
        else:
            backgroud_image_V = t.background_image_vertical

        source_img = get_tmp_local_path(t.image)
        backgroud_image_H = get_tmp_local_path(backgroud_image_H)
        backgroud_image_V = get_tmp_local_path(backgroud_image_V) if backgroud_image_V is not None else None
        return full_task, source_img, backgroud_image_V, backgroud_image_H, t.rate_width, t.border_size, t.resize_width

    @classmethod
    @retry(tries=2, delay=1, backoff=1, max_delay=3)
    def exec_seg(cls, img_path):
        @timeout(30)
        def time_control(img_path):
            logger.info(f"pixian seg progress......")
            url = 'https://api.pixian.ai/api/v2/remove-background'
            response = requests.post(url,
                                     files={'image': open(img_path, 'rb')},
                                     headers={
                                         'Authorization': 'Basic cHhhMmF2bGo3ODMzcjZhOjY1NmFlMnAzdDhiNm1vbTFhM2t1dnAxZ2ZzODEwcTMzNzk4MzEydWhnOTFoaGh0ZzZjZnY='
                                     }, timeout=30)
            logger.info("seg post process....")
            if response.status_code == requests.codes.ok:
                logger.info("seg write....")
                stream = BytesIO(response.content)
                logger.info("open  start....")
                res = Image.open(stream)
                logger.info("open  end....")
                return res
            else:
                logger.error(f"pixian seg Error:, {response.status_code}, {response.text}")

                raise Exception("pixian api get failed")

        return time_control(img_path)

    # 图片加背景图片:贴空白背景，贴竖图背景，贴横图背景
    @classmethod
    def exec_add_back(cls, imq, back_path_V=None, back_path_H=None, rate_width=0.25, scale=1):
        logger.info(f"add background progress......")
        # 生成图的尺寸是：1152*864
        if not isinstance(imq, Image.Image):
            imq = Image.open(imq)
        # 如果是横图背景(2048x1152,调大小并且居左/中/右+尺寸)
        if back_path_H is not None:
            if not isinstance(back_path_H, Image.Image):
                img = Image.open(back_path_H)
            else:
                img = back_path_H
            imq = imq.resize((int(imq.size[0] * scale), int(imq.size[1] * scale)))
            r, g, b, a = imq.split()
            width, height = imq.size
            width_b, height_b = img.size
            if width_b * rate_width > width_b - width:
                img.paste(imq, (int(width_b - width), height_b - height, width_b,
                                height_b), mask=a)  # 贴背景
            else:
                img.paste(imq, (int(width_b * rate_width), height_b - height, width + int(width_b * rate_width),
                                height_b), mask=a)  # 贴背景
            return img
        # 如果是竖图背景（裁剪到768*1152，贴到背景上）
        elif back_path_V is not None:
            if not isinstance(back_path_V, Image.Image):
                img = Image.open(back_path_V)
            else:
                img = back_path_V
            # 裁剪了再贴
            width_b, height_b = img.size
            width, height = imq.size
            # 如果超了 就截取最右边
            if width * rate_width > width - width_b:
                imq = imq.crop((int(width - width_b), height - 1152, width, height))
            else:
                print((int(width * rate_width), height - 1152, 768 + int(width * rate_width), height))
                imq = imq.crop((int(width * rate_width), height - 1152, 768 + int(width * rate_width), height))
            r, g, b, a = imq.split()
            width, height = imq.size
            print(width, height)
            img.paste(imq, (0, height_b - height, width_b, height_b), mask=a)
            return img
        else:
            # 白背景的贴合：根据背景的位置,得到往左/右延展的白色背景底图，底图的大小是背景的一半（864, 1152）,宽度可以调整一下
            img = 255 * np.ones((864, 1152, 3), np.uint8)
            img = Image.fromarray(img)
            width_b, height_b = img.size
            ta = max(imq.size[0] / 576, imq.size[1] / 768)
            imq = LaternFairTask.pad_image_to_size(imq, (int(576 * ta), int(768 * ta)))
            imq = imq.resize((576, 768))
            r, g, b, a = imq.split()
            width, height = imq.size
            # 贴在右边：如果超了，就以超的边缘为准
            if width_b * rate_width > width_b - width:
                img.paste(imq, (int(width_b - width), height_b - height, width_b, height_b),
                          mask=a)  # 贴背景
            else:
                img.paste(imq, (int(width_b * rate_width), height_b - height, width + int(width_b * rate_width),
                                height_b), mask=a)  # 贴背景
        return img

    # 边缘模糊
    @classmethod
    def canny_blur(cls, image: Image.Image, border_size=160):
        # 获取图像大小
        width, height = image.size
        # 创建一个新的透明图像
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        # 设置边框透明度渐变
        for y in range(height):
            for x in range(width):
                r, g, b, a = image.getpixel((x, y))
                if x < border_size or x >= width - border_size or y < border_size or y >= height - border_size:
                    alpha = int((min(x, y, width - x - 1, height - y - 1) / border_size) * a)  # 根据距离边框的距离计算透明度
                    result.putpixel((x, y), (r, g, b, alpha))
                else:
                    result.putpixel((x, y), (r, g, b, a))
        return result

    @classmethod
    def pad_image_to_size(cls, image, target_size):
        width, height = image.size
        target_width, target_height = target_size

        if width >= target_width and height >= target_height:
            return image  # 图像已经大于或等于目标尺寸，无需补全

        # 计算需要补全的宽度和高度
        pad_width = max(target_width - width, 0)
        pad_height = max(target_height - height, 0)

        # 计算补全的边距
        left = pad_width // 2
        top = pad_height // 2
        # 创建一个新的画布，并将图像粘贴到居中靠下位置
        padded_image = Image.new('RGBA', target_size, (0, 0, 0, 0))
        padded_image.paste(image, (left, target_height - height, width + left, target_height))

        return padded_image

class KidDrawingTask(Txt2ImgTask):
    def __init__(self,
                 images: List,  # 功能类型
                 args: dict,  # 极速模式
                 ):
        self.images = images
        self.args = args
    @classmethod
    def exec_task(cls, task: Task):
        t = KidDrawingTask(
            task['images'],
            task['args']
        )
        extra_args = deepcopy(task['args'])
        full_task = deepcopy(task)
        full_task.pop("args")
        # full_task.pop("images")
        full_task.update(extra_args)

        img_batch =[]
        for img in t.images:
            img_batch.append(get_tmp_local_path(img))
        # lora拼接
        lora_promts=""
        for i in range(0,len(full_task['lora_list'])):
            lora_hash,lora_weight=full_task['lora_list'][i]['hash'],full_task['lora_list'][i]['value']
            lora_promt=f"<lora:{lora_hash}:{lora_weight}>,"
            lora_promts+=lora_promt

        return img_batch,full_task,lora_promts


class OnePressTaskHandler(Txt2ImgTaskHandler):
    def __init__(self):
        super(OnePressTaskHandler, self).__init__()
        self.task_type = TaskType.OnePress

    def _exec(self, task: Task) -> typing.Iterable[TaskProgress]:
        # 根据任务的不同类型：执行不同的任务
        if task.minor_type == OnePressTaskType.Conversion:
            yield from self._exec_conversion(task)
        elif task.minor_type == OnePressTaskType.Rendition:
            yield from self._exec_rendition(task)
        elif task.minor_type == OnePressTaskType.ImgToGif:
            yield from self._exec_img2gif(task)
        elif task.minor_type == OnePressTaskType.ArtWord:
            yield from self._exec_artword(task)
        elif task.minor_type == OnePressTaskType.LaternFair:
            yield from self._exec_laternfair(task)
        elif task.minor_type == OnePressTaskType.SegImg:
            yield from self._exec_segimage(task)
        elif task.minor_type== OnePressTaskType.KidDrawring:
            yield from self._exec_kiddrawing(task)
        else:
            raise Exception(f'TaskType {self.task_type}, minor_type {task.minor_type} does not exist')

    def _build_gen_canny_i2i_args(self, t, processed: Processed):
        denoising_strength = 0.5
        cfg_scale = 7

        p = StableDiffusionProcessingImg2Img(
            sd_model=shared.sd_model,
            outpath_samples=t.outpath_samples,
            outpath_grids=t.outpath_grids,
            prompt=t.prompt,
            negative_prompt=t.negative_prompt,
            seed=-1,
            subseed=-1,
            sampler_name=t.sampler_name,
            batch_size=1,
            n_iter=1,
            steps=t.steps,
            cfg_scale=cfg_scale,
            width=t.width,
            height=t.height,
            restore_faces=t.restore_faces,
            tiling=t.tiling,
            init_images=processed.images,
            mask=None,
            denoising_strength=denoising_strength

        )

        p.outpath_scripts = t.outpath_grids

        return p

    def _canny_process_i2i(self, p, alwayson_scripts):
        fix_seed(p)

        images = p.init_images

        save_normally = True

        p.do_not_save_grid = True
        p.do_not_save_samples = not save_normally

        shared.state.job_count = len(images) * p.n_iter

        image = images[0]
        shared.state.job = f"{1} out of {len(images)}"

        # Use the EXIF orientation of photos taken by smartphones.
        img = ImageOps.exif_transpose(image)
        p.init_images = [img] * p.batch_size

        i2i_script_runner = modules.scripts.scripts_img2img
        default_script_arg_img2img = init_default_script_args(
            modules.scripts.scripts_img2img)
        selectable_scripts, selectable_script_idx = get_selectable_script(
            i2i_script_runner, None)
        select_script_args = ''
        script_args = init_script_args(default_script_arg_img2img, alwayson_scripts, selectable_scripts,
                                       selectable_script_idx, select_script_args, i2i_script_runner)
        script_args = tuple(script_args)

        p.scripts = i2i_script_runner
        p.script_args = script_args
        p.override_settings = {'sd_vae': 'None'}
        proc = modules.scripts.scripts_img2img.run(p, *script_args)
        if proc is None:
            proc = process_images(p)
        # 只返回第一张
        proc.images = [proc.images[0]]
        return proc

    def _exec_conversion(self, task: Task) -> typing.Iterable[TaskProgress]:
        logger.info("one press conversion func starting...")
        full_task, is_img2img, full_canny, part_canny = ConversionTask.exec_task(
            task)
        logger.info("download model...")
        # 加载模型
        base_model_path = self._get_local_checkpoint(full_task)
        logger.info(f"load model:{base_model_path}")
        load_sd_model_weights(base_model_path, full_task.model_hash)

        # 第一阶段 上色
        progress = TaskProgress.new_ready(
            full_task, f'model loaded, run onepress_paint...')
        yield progress

        logger.info("download network models...")
        process_args = self._build_img2img_arg(
            progress) if is_img2img else self._build_txt2img_arg(progress)
        self._set_little_models(process_args)
        progress.status = TaskStatus.Running
        progress.task_desc = f'onepress task({task.id}) running'
        yield progress

        logger.info("step 1, colour...")
        shared.state.begin()
        processed = process_images(process_args)
        logger.info("step 1 > ok")
        # 第二阶段 细化
        if part_canny or full_canny:
            alwayson_scripts = {}
            if part_canny:
                alwayson_scripts.update(get_llul_args())
            if full_canny:
                alwayson_scripts.update(get_multidiffusion_args())
            # i2i
            logger.info("step 2, canny...")
            processed_i2i_1 = self._build_gen_canny_i2i_args(
                process_args, processed)
            processed_i2i = self._canny_process_i2i(
                processed_i2i_1, alwayson_scripts)
            processed.images = processed_i2i.images
        logger.info("step 2 > ok")
        shared.state.end()
        process_args.close()

        logger.info("step 3, upload images...")
        progress.status = TaskStatus.Uploading
        yield progress

        # 只返回最终结果图
        processed.images = [processed.images[0]]
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))
        logger.info("step 3 > ok")
        progress = TaskProgress.new_finish(task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)

        yield progress

    def _exec_rendition(self, task: Task) -> typing.Iterable[TaskProgress]:

        # TODO 测试xl的使用，更新task参数
        logger.info("one press rendition func starting...")
        full_task, is_img2img = RenditionTask.exec_task(task)

        # 适配xl
        logger.info("download model...")
        local_model_paths = self._get_local_checkpoint(full_task)
        base_model_path = local_model_paths if not isinstance(
            local_model_paths, tuple) else local_model_paths[0]
        refiner_checkpoint = None if not isinstance(
            local_model_paths, tuple) else local_model_paths[1]

        load_sd_model_weights(base_model_path, full_task.model_hash)
        progress = TaskProgress.new_ready(
            full_task, f'model loaded, run t2i...')
        yield progress

        # 更新图生图模式，xl模式
        process_args = self._build_txt2img_arg(
            progress, refiner_checkpoint) if not is_img2img else self._build_img2img_arg(progress, refiner_checkpoint)

        self._set_little_models(process_args)
        progress.status = TaskStatus.Running
        progress.task_desc = f'onepress task({task.id}) running'
        yield progress
        logger.info("step 1, rendition...")
        shared.state.begin()
        processed = process_images(process_args)
        # processed.images = processed.images[1:task['batch_size']+1]
        logger.info("step 1 > ok")

        # 如果需要换人脸
        if task['roop']:
            logger.info("step 2, roop...")
            roop_result = []
            for i, img in enumerate(processed.images):
                source_img = get_tmp_local_path(task['image'])
                source_img = Image.open(source_img).convert('RGB')
                target_img = img  #
                # source_img: Image.Image, target_img: Image.Image,
                roop_result.append(
                    RenditionTask.exec_roop(source_img, target_img))
            processed.images = roop_result
            logger.info("step 2 > ok")

        shared.state.end()
        process_args.close()
        logger.info("step 3, upload images...")
        progress.status = TaskStatus.Uploading
        yield progress
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))
        logger.info("step 3 > ok")
        progress = TaskProgress.new_finish(task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)
        yield progress

    def _exec_img2gif(self, task: Task) -> typing.Iterable[TaskProgress]:
        # 整体流程：1.拿到原图+抠图+贴白背景+生成序列帧：图生图+animatediff+controlnet（refenrence——only，softedge）
        # （万能提示词+tagger反推提示词+表情标签提示词，负向提示词）
        # TODO 测试xl的使用，更新task参数

        logger.info("one press img2gif func starting...")
        full_task, is_img2img = ImgtoGifTask.exec_task(task)

        # 适配xl    ``
        logger.info("download model...")
        local_model_paths = self._get_local_checkpoint(full_task)
        base_model_path = local_model_paths if not isinstance(
            local_model_paths, tuple) else local_model_paths[0]
        refiner_checkpoint = None if not isinstance(
            local_model_paths, tuple) else local_model_paths[1]

        load_sd_model_weights(base_model_path, full_task.model_hash)
        progress = TaskProgress.new_ready(
            full_task, f'model loaded, run speed...')
        yield progress

        # 图生图模式
        process_args = self._build_img2img_arg(progress, refiner_checkpoint)

        self._set_little_models(process_args)
        progress.status = TaskStatus.Running
        progress.task_desc = f'onepress task({task.id}) running'
        yield progress
        logger.info("step 1, img2gif...")
        shared.state.begin()
        processed = process_images(process_args)
        # processed.images = processed.images[1:task['batch_size']+1]
        logger.info("step 1 > ok")

        shared.state.end()
        process_args.close()
        logger.info("step 2, upload images...")
        progress.status = TaskStatus.Uploading
        yield progress
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))
        logger.info("step 3 > ok")
        progress = TaskProgress.new_finish(task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)
        yield progress

    def _exec_artword(self, task: Task) -> typing.Iterable[TaskProgress]:
        logger.info("one press artword func starting...")
        full_task, is_img2img = ArtWordTask.exec_task(task)

        # 适配xl
        logger.info("download model...")
        local_model_paths = self._get_local_checkpoint(full_task)
        base_model_path = local_model_paths if not isinstance(
            local_model_paths, tuple) else local_model_paths[0]
        refiner_checkpoint = None if not isinstance(
            local_model_paths, tuple) else local_model_paths[1]

        load_sd_model_weights(base_model_path, full_task.model_hash)
        progress = TaskProgress.new_ready(
            full_task, f'model loaded, run t2i...')
        yield progress

        # 更新图生图模式，xl模式
        process_args = self._build_txt2img_arg(
            progress, refiner_checkpoint) if not is_img2img else self._build_img2img_arg(progress, refiner_checkpoint)

        self._set_little_models(process_args)
        progress.status = TaskStatus.Running
        progress.task_desc = f'onepress task({task.id}) running'
        yield progress
        logger.info("step 1, artword...")
        shared.state.begin()
        processed = process_images(process_args)
        # processed.images = processed.images[1:task['batch_size']+1]
        logger.info("step 1 > ok")

        # 如果需要换人脸
        if task['roop']:
            logger.info("step 2, roop...")
            roop_result = []
            for i, img in enumerate(processed.images):
                source_img = get_tmp_local_path(task['image'])
                source_img = Image.open(source_img).convert('RGB')
                target_img = img  #
                # source_img: Image.Image, target_img: Image.Image,
                roop_result.append(
                    RenditionTask.exec_roop(source_img, target_img))
            processed.images = roop_result
            logger.info("step 2 > ok")

        shared.state.end()
        process_args.close()
        logger.info("step 3, upload images...")
        progress.status = TaskStatus.Uploading
        yield progress
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))
        logger.info("step 3 > ok")
        progress = TaskProgress.new_finish(task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)
        yield progress

    def _exec_laternfair(self, task: Task) -> typing.Iterable[TaskProgress]:

        full_task, user_image, backgroud_image_V, backgroud_image_H, rate_width, border_size, scale = LaternFairTask.exec_task(
            task)
        # 适配xl
        logger.info("laternfair download model...")
        local_model_paths = self._get_local_checkpoint(full_task)
        base_model_path = local_model_paths if not isinstance(
            local_model_paths, tuple) else local_model_paths[0]
        refiner_checkpoint = None if not isinstance(
            local_model_paths, tuple) else local_model_paths[1]

        logger.info(f"laternfair loaded base model {full_task.model_hash} ....")
        load_sd_model_weights(base_model_path, full_task.model_hash)

        progress = TaskProgress.new_ready(
            full_task, f'model loaded, run laternfairtask...', eta_relative=70)
        yield progress

        progress.fixed_eta = random.randint(12, 15)  # 加上后面抠图和贴背景的时间

        process_args = self._build_txt2img_arg(progress)

        logger.info("laternfair loaded lora model ....")
        self._set_little_models(process_args)  # 加载lora

        progress.status = TaskStatus.Running

        progress.task_desc = f'laternfairtask task({task.id}) running'
        yield progress

        logger.info("step 1, seg...")
        # 备选方案：rmf抠图
        try:
            seg_image = LaternFairTask.exec_seg(user_image)
        except:
            seg_image = rmf_seg(user_image)
        # 添加白色背景
        white_image = LaternFairTask.exec_add_back(seg_image, rate_width=rate_width, scale=scale)
        logger.info("step 1 > ok")
        # 重新赋值controlnet参数
        args_from, args_to = 0, 0
        for script in process_args.scripts.scripts:
            if script.title() == "ControlNet":
                args_from = script.args_from
                args_to = script.args_to
        all_cn_args = deepcopy(process_args.script_args_value[args_from: args_to])
        for index, cn_arg in enumerate(process_args.script_args_value[args_from: args_to]):
            if isinstance(cn_arg, Dict):
                tmp_cn_args = deepcopy(cn_arg)
                tmp_cn_args['image']['image'] = np.array(white_image)
                all_cn_args[index] = tmp_cn_args
        process_args.script_args_value[args_from: args_to] = all_cn_args
        logger.info("step 2, txt2img...")
        shared.state.begin()
        processed = process_images(process_args)
        shared.state.end()
        process_args.close()

        logger.info("step 3, mosaic background main picture...")

        # 拿到结果图后,抠图，边缘模糊，加背景
        txt2img_image = processed.images[0]
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        file_path = temp_file.name
        txt2img_image.save(file_path)
        # 备选方案：rmf抠图
        try:
            txt2img_seg_image = LaternFairTask.exec_seg(file_path)
        except:
            txt2img_seg_image = rmf_seg(file_path)

        blur_image = LaternFairTask.canny_blur(txt2img_seg_image, border_size)
        # 添加横图背景
        txt2img_backgroud_image_H = LaternFairTask.exec_add_back(blur_image, back_path_V=None,
                                                                 back_path_H=backgroud_image_H, rate_width=rate_width,
                                                                 scale=scale)
        # 添加竖图背景
        txt2img_backgroud_image_V = LaternFairTask.exec_add_back(blur_image, back_path_V=backgroud_image_V,
                                                                 back_path_H=None, rate_width=rate_width, scale=scale)
        processed.images.insert(processed.index_of_end_image, txt2img_backgroud_image_H)
        processed.index_of_end_image += 1
        processed.all_seeds += [1]
        processed.all_subseeds += [1]
        processed.images[1] = txt2img_backgroud_image_V

        logger.info("step 3 > ok")

        logger.info("step 4, upload images...")
        progress.eta_relative = 5
        progress.status = TaskStatus.Uploading
        yield progress
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))

        progress = TaskProgress.new_finish(task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)
        yield progress
    
    def _exec_segimage(self, task: Task) -> typing.Iterable[TaskProgress]:
        #输入：需要抠的图片
        logger.info(f"onepress segimage beigin.....,{task['task_id']}")
        progress = TaskProgress.new_ready(
            task, f'get_local_file finished, run seg image...')
        yield progress
        target_path=task['image']
        logger.info(f"onepress segimage get_local_file.....,{target_path}")
        target_face = get_tmp_local_path(target_path)
        progress.status = TaskStatus.Running
        progress.task_desc = f'onepress segimage task({task.id}) running'
        seg_image = rmf_seg(target_face)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        file_path = temp_file.name
        seg_image.save(file_path)
        try:
            progress.status = TaskStatus.Uploading
            current_date = datetime.datetime.now()
            formatted_date = current_date.strftime('%Y-%m-%d')
            remoting,local=f'media/{formatted_date}/{os.path.basename(file_path)}',file_path
            oss_key=push_local_path(remoting,local)
            yield progress
            progress = TaskProgress.new_finish(task, {
                    "all": {
                        "high": [oss_key]
                    }
                })
            progress.task_desc = f'onepress segimage task:{task.id} finished.'
            yield progress

        except Exception as e:
            progress.status = TaskStatus.Failed
            progress.task_desc = f'onepress segimage task:{task.id} failed.{e}'
            yield progress

    def _exec_kiddrawing(self, task: Task) -> typing.Iterable[TaskProgress]:
        img_batch,full_task,lora_promts = KidDrawingTask.exec_task(
            task)
        # 适配xl
        logger.info("laternfair kid drawing download model...")
        local_model_paths = self._get_local_checkpoint(full_task)
        base_model_path = local_model_paths if not isinstance(
            local_model_paths, tuple) else local_model_paths[0]
        refiner_checkpoint = None if not isinstance(
            local_model_paths, tuple) else local_model_paths[1]

        logger.info(f"laternfair kid drawing loaded base model {full_task.model_hash} ....")
        load_sd_model_weights(base_model_path, full_task.model_hash)

        progress = TaskProgress.new_ready(full_task, f'model loaded, run laternfair kid drawing task...')
        yield progress

        process_args = self._build_img2img_arg(progress)

        logger.info(" laternfair kid drawing loaded lora model ....")
        self._set_little_models(process_args)  # 加载lora

        progress.status = TaskStatus.Running
        progress.task_desc = f' laternfair kid drawing task({task.id}) running'
        yield progress
        logger.info("step 1, txt2img...")
        shared.state.begin()
        all_imgs=[]
        for idex,img in enumerate(img_batch):
            pil_img=Image.open(img)
            promt=shared.interrogator.interrogate(pil_img)
            process_args.prompt="lamp,luminescence,Lamp group,Lantern Festival,lantern,"+promt+lora_promts
            process_args.width=1653 if pil_img.size[0]>pil_img.size[1] else 1167
            process_args.height=1167 if pil_img.size[0]>pil_img.size[1] else 1653
            process_args.init_images=[pil_img]
            processed = process_images(process_args)
            all_imgs.append( processed.images[0])
            progress.eta_relative = (idex+1)/len(img_batch)*100 # 加上后面抠图和贴背景的时间
            progress.task_progress=(idex+1)/len(img_batch)*100
            yield progress
        shared.state.end()
        process_args.close()

        logger.info("step 3, mosaic background main picture...")

        processed.images=all_imgs
        processed.index_of_end_image =len(processed.images)
        processed.all_seeds += [1]*len(processed.images)
        processed.all_subseeds += [1]*len(processed.images)
        logger.info("step 3 > ok")

        logger.info("step 4, upload images...")
        progress.eta_relative = 5
        progress.status = TaskStatus.Uploading
        yield progress
        images = save_processed_images(processed,
                                       process_args.outpath_samples,
                                       process_args.outpath_grids,
                                       process_args.outpath_scripts,
                                       task.id,
                                       inspect=process_args.kwargs.get("need_audit", False))

        progress = TaskProgress.new_finish(full_task, images)
        progress.update_seed(processed.all_seeds, processed.all_subseeds)
        yield progress
