"""
 Copyright (c) 2020 Intel Corporation
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

from __future__ import division, absolute_import
import torch.nn as nn

from torchreid.losses import AngleSimpleLinear

from functools import partial
from pytorchcv.model_provider import _models, get_model

from .common import ModelInterface

__all__ = ['wrapped_models']

def conv1x1(in_channels,
            out_channels,
            stride=1,
            groups=1,
            bias=False):
    """
    Convolution 1x1 layer.
    Parameters:
    ----------
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels.
    stride : int or tuple/list of 2 int, default 1
        Strides of the convolution.
    groups : int, default 1
        Number of groups.
    bias : bool, default False
        Whether the layer uses a bias vector.
    """
    return nn.Conv2d(
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=1,
        stride=stride,
        groups=groups,
        bias=bias)


class PTCVModel(ModelInterface):
    def __init__(
        self,
        model_name,
        num_classes,
        loss='softmax',
        IN_first=False,
        pooling_type='avg',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.pooling_type = pooling_type
        self.loss = loss
        assert isinstance(num_classes, int)

        model = get_model(model_name, num_classes=1000, pretrained=self.pretrained)
        assert hasattr(model, 'features') and isinstance(model.features, nn.Sequential)
        self.features = model.features
        self.features = self.features[:-1] # remove pooling, since it can have a fixed size
        if self.loss not in ['am_softmax']:
            self.output_conv = nn.Conv2d(in_channels=model.output.in_channels, out_channels=num_classes, kernel_size=1, stride=1, bias=False)
        else:
            self.output_conv = AngleSimpleLinear(model.output.in_channels, num_classes)
            self.feature_dim = model.output.in_channels

        self.input_IN = nn.InstanceNorm2d(3, affine=True) if IN_first else None

    def forward(self, x, return_featuremaps=False, get_embeddings=False):
        if self.input_IN is not None:
            x = self.input_IN(x)

        y = self.features(x)
        if return_featuremaps:
            return y

        glob_features = self._glob_feature_vector(y, self.pooling_type, reduce_dims=False)

        logits = self.output_conv(glob_features).view(x.shape[0], -1)

        if not self.training and self.classification:
            return [logits]

        if get_embeddings:
            out_data = [logits, glob_features.view(x.size(0), -1)]
        elif self.loss in ['softmax', 'am_softmax']:
            out_data = [logits]
        elif self.loss in ['triplet']:
            out_data = [logits, glob_features.view(x.size(0), -1)]
        else:
            raise KeyError("Unsupported loss: {}".format(self.loss))

        return tuple(out_data)


wrapped_models = {'ptcv_' + name : partial(PTCVModel, model_name=name) for name in _models.keys()}
