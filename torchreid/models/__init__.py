from __future__ import absolute_import

from .densenet import *
from .efficient_net_pytcv import *
from .hacnn import *
from .inceptionresnetv2 import *
from .inceptionv4_pytcv import *
from .mlfn import *
from .mobile_face_net_se import *
from .mobilenetv2 import *
from .mobilenetv3 import *
from .mudeep import *
from .nasnet import *
from .osnet import *
from .osnet_ain import *
from .osnet_fpn import *
from .pcb import *
from .ptcv_wrapper import *
from .res2net import *
from .resnet import *
from .resnet_ibn_a import *
from .resnet_ibn_b import *
from .resnetmid import *
from .senet import *
from .shufflenet import *
from .shufflenetv2 import *
from .squeezenet import *
from .xception import *
from .mobilenetv3_small_v2 import *

__model_factory = {
    # image classification models
    'resnet18': resnet18,
    'resnet34': resnet34,
    'resnet50': resnet50,
    'resnet101': resnet101,
    'resnet152': resnet152,
    'resnext50_32x4d': resnext50_32x4d,
    'resnext101_32x8d': resnext101_32x8d,
    'resnet50_fc512': resnet50_fc512,
    'se_resnet50': se_resnet50,
    'se_resnet50_fc512': se_resnet50_fc512,
    'se_resnet101': se_resnet101,
    'se_resnext50_32x4d': se_resnext50_32x4d,
    'se_resnext101_32x4d': se_resnext101_32x4d,
    'densenet121': densenet121,
    'densenet169': densenet169,
    'densenet201': densenet201,
    'densenet161': densenet161,
    'inceptionresnetv2': inceptionresnetv2,
    'inceptionv4_pytcv': inceptionv4_pytcv,
    'xception': xception,
    'resnet50_ibn_a': resnet50_ibn_a,
    'resnet50_ibn_b': resnet50_ibn_b,
    # lightweight models
    'nasnsetmobile': nasnetamobile,
    'mobilenetv2_x1_0': mobilenetv2_x1_0,
    'mobilenetv2_x1_4': mobilenetv2_x1_4,
    'mobilenetv3_small': mobilenetv3_small,
    'mobilenetv3_small_v2': mobilenetv3_small_v2,
    'mobilenetv3_large': mobilenetv3_large,
    'mobilenetv3_large_075': mobilenetv3_large_075,
    'mobilenetv3_large_150': mobilenetv3_large_150,
    'mobilenetv3_large_125': mobilenetv3_large_125,
    'MobileNetV3_large_100_timm': MobileNetV3_large_100_timm,
    'shufflenet': shufflenet,
    'squeezenet1_0': squeezenet1_0,
    'squeezenet1_0_fc512': squeezenet1_0_fc512,
    'squeezenet1_1': squeezenet1_1,
    'shufflenet_v2_x0_5': shufflenet_v2_x0_5,
    'shufflenet_v2_x1_0': shufflenet_v2_x1_0,
    'shufflenet_v2_x1_5': shufflenet_v2_x1_5,
    'shufflenet_v2_x2_0': shufflenet_v2_x2_0,
    # reid-specific models
    'mudeep': MuDeep,
    'resnet50mid': resnet50mid,
    'hacnn': HACNN,
    'pcb_p6': pcb_p6,
    'pcb_p4': pcb_p4,
    'mlfn': mlfn,
    'osnet_x1_0': osnet_x1_0,
    'osnet_x0_75': osnet_x0_75,
    'osnet_x0_5': osnet_x0_5,
    'osnet_x0_25': osnet_x0_25,
    'osnet_ibn_x1_0': osnet_ibn_x1_0,
    'osnet_ain_x1_0': osnet_ain_x1_0,
    'osnet_ain2_x1_0': osnet_ain2_x1_0,
    'fpn_osnet_x1_0': fpn_osnet_x1_0,
    'fpn_osnet_x0_75': fpn_osnet_x0_75,
    'fpn_osnet_x0_5': fpn_osnet_x0_5,
    'fpn_osnet_x0_25': fpn_osnet_x0_25,
    'fpn_osnet_ibn_x1_0': fpn_osnet_ibn_x1_0,
    'res2net50_v1b': res2net50_v1b_26w_4s,
    'res2net101_v1b': res2net101_v1b_26w_4s,
    # face reid models
    'mobile_face_net_se_1x': mobile_face_net_se_1x,
    'mobile_face_net_se_2x': mobile_face_net_se_2x,
    'efficientnet_b0': efficientnet_b0,
    'efficientnet_b1': efficientnet_b1,
    'efficientnet_b2': efficientnet_b2b,
    'efficientnet_b3': efficientnet_b3b,
    'efficientnet_b4': efficientnet_b4b,
    'efficientnet_b5': efficientnet_b5b,
    'efficientnet_b6': efficientnet_b6b,
    'efficientnet_b7': efficientnet_b7b,
}

__model_factory = {**__model_factory, **wrapped_models}


def show_avai_models():
    """Displays available models.

    Examples::
        >>> from torchreid import models
        >>> models.show_avai_models()
    """
    print(list(__model_factory.keys()))


def build_model(name, **kwargs):
    """A function wrapper for building a model.

    Args:
        name (str): model name.

    Returns:
        nn.Module

    Examples::
        >>> from torchreid import models
        >>> model = models.build_model('resnet50', 751, loss='softmax')
    """
    avai_models = list(__model_factory.keys())
    if name not in avai_models:
        raise KeyError('Unknown model: {}. Must be one of {}'.format(name, avai_models))
    print(__model_factory[name])
    return __model_factory[name](**kwargs)
