import torch
import torch.nn as nn

from itertools import chain


def map_device(outputs, output_device):
    if isinstance(outputs, torch.Tensor):
        return outputs.to(output_device)
    elif isinstance(outputs, (tuple, list)):
        return [map_device(o, output_device) for o in outputs]
    elif isinstance(outputs, dict):
        return {k: map_device(v, output_device) for k, v in outputs.items()}
    else:
        raise ValueError('Unknown output type: {}'.format(type(outputs)))


class DataParallel(nn.DataParallel):
    def forward(self, *inputs, **kwargs):
        if not self.device_ids:
            return self.module(*inputs, **kwargs)

        for t in chain(self.module.parameters(), self.module.buffers()):
            if t.device != self.src_device_obj:
                raise RuntimeError("module must have its parameters and buffers "
                                   "on device {} (device_ids[0]) but found one of "
                                   "them on device: {}".format(self.src_device_obj, t.device))

        inputs, kwargs = self.scatter(inputs, kwargs, self.device_ids)

        if len(self.device_ids) == 1:
            outputs = self.module(*inputs[0], **kwargs[0])
            return map_device(outputs, self.output_device)

        replicas = self.replicate(self.module, self.device_ids[:len(inputs)])
        outputs = self.parallel_apply(replicas, inputs, kwargs)

        return self.gather(outputs, self.output_device)
