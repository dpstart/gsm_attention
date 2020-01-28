import torch
from torch import nn
from .layer_factory import get_basic_layer, parse_expr, build_gsm, build_attention
import torch.utils.model_zoo as model_zoo
import yaml

class BNInception(nn.Module):
    def __init__(self, model_path='model_zoo/bninception/bn_inception.yaml', num_classes=101,
                       weight_url='https://yjxiong.blob.core.windows.net/models/bn_inception-9f5701afb96c8044.pth'):
        super(BNInception, self).__init__()

        manifest = yaml.load(open(model_path))

        layers = manifest['layers']

        self._channel_dict = dict()

        self._op_list = list()
        for l in layers:
            out_var, op, in_var = parse_expr(l['expr'])
            if op != 'Concat':
                id, out_name, module, out_channel, in_name = get_basic_layer(l,
                                                                3 if len(self._channel_dict) == 0 else self._channel_dict[in_var[0]],
                                                                             conv_bias=True)

                self._channel_dict[out_name] = out_channel
                setattr(self, id, module)
                self._op_list.append((id, op, out_name, in_name))
            else:
                self._op_list.append((id, op, out_var[0], in_var))
                channel = sum([self._channel_dict[x] for x in in_var])
                self._channel_dict[out_var[0]] = channel

        state_dict = torch.utils.model_zoo.load_url(weight_url)
        for k, v in state_dict.items():
            state_dict[k] = torch.squeeze(v, dim=0)
        self.load_state_dict(state_dict)


    def forward(self, input):
        data_dict = dict()
        data_dict[self._op_list[0][-1]] = input

        def get_hook(name):

            def hook(m, grad_in, grad_out):
                print(name, grad_out[0].data.abs().mean())

            return hook
        for op in self._op_list:
            if op[1] != 'Concat' and op[1] != 'InnerProduct':
                data_dict[op[2]] = getattr(self, op[0])(data_dict[op[-1]])
                # getattr(self, op[0]).register_backward_hook(get_hook(op[0]))
                print(data_dict[op[2]].size())
            elif op[1] == 'InnerProduct':
                x = data_dict[op[-1]]
                data_dict[op[2]] = getattr(self, op[0])(x.view(x.size(0), -1))
            else:
                try:
                    data_dict[op[2]] = torch.cat(tuple(data_dict[x] for x in op[-1]), 1)
                except:
                    for x in op[-1]:
                        print(x,data_dict[x].size())
                    raise
        return data_dict[self._op_list[-1][2]]

class BNInception_gsm(nn.Module):
    def __init__(self, model_path='model_zoo/bninception/bn_inception_gsm.yaml', num_classes=101,
                       weight_url='https://yjxiong.blob.core.windows.net/models/bn_inception-9f5701afb96c8044.pth',
                       num_segments=16):
        super(BNInception_gsm, self).__init__()

        manifest = yaml.load(open(model_path))

        layers = manifest['layers']

        self._channel_dict = dict()

        self._op_list = list()
        hGates_cnt = 0
        for l in layers:
            out_var, op, in_var = parse_expr(l['expr'])
            if op != 'Concat':
                if op == 'gsm':
                    hGates_cnt += 1
                    id, out_name, module, out_channel, in_name = build_gsm(l,  self._channel_dict[in_var[0]],
                                                                                 conv_bias=True, num_segments=num_segments)

                    self._channel_dict[out_name] = out_channel
                    setattr(self, id, module)
                    self._op_list.append((id, op, out_name, in_name))
                else:
                    id, out_name, module, out_channel, in_name = get_basic_layer(l,
                                                                    3 if len(self._channel_dict) == 0 else self._channel_dict[in_var[0]],
                                                                                 conv_bias=True)

                    self._channel_dict[out_name] = out_channel
                    setattr(self, id, module)
                    self._op_list.append((id, op, out_name, in_name))
            else:
                self._op_list.append((id, op, out_var[0], in_var))
                channel = sum([self._channel_dict[x] for x in in_var])
                self._channel_dict[out_var[0]] = channel

        state_dict = torch.utils.model_zoo.load_url(weight_url)
        for k, v in state_dict.items():
            state_dict[k] = torch.squeeze(v, dim=0)
        self.load_state_dict(state_dict, strict=False)

    def forward(self, input):
        data_dict = dict()
        data_dict[self._op_list[0][-1]] = input

        def get_hook(name):

            def hook(m, grad_in, grad_out):
                print(name, grad_out[0].data.abs().mean())

            return hook
        for op in self._op_list:
            if op[1] != 'Concat' and op[1] != 'InnerProduct':
                data_dict[op[2]] = getattr(self, op[0])(data_dict[op[-1]])
                # getattr(self, op[0]).register_backward_hook(get_hook(op[0]))
            elif op[1] == 'InnerProduct':
                x = data_dict[op[-1]]
                data_dict[op[2]] = getattr(self, op[0])(x.view(x.size(0), -1))
            else:
                try:
                    data_dict[op[2]] = torch.cat(tuple(data_dict[x] for x in op[-1]), 1)
                except:
                    for x in op[-1]:
                        print(x,data_dict[x].size())
                    raise
        return data_dict[self._op_list[-1][2]]

    

class BNInception_gsm_attention(nn.Module):
    def __init__(self, model_path='model_zoo/bninception/bn_inception_gsm_attention.yaml', num_classes=101,
                       weight_url='https://yjxiong.blob.core.windows.net/models/bn_inception-9f5701afb96c8044.pth',
                       num_segments=16, attention_type='general'):
        super(BNInception_gsm_attention, self).__init__()

        manifest = yaml.load(open(model_path))

        layers = manifest['layers']

        self._channel_dict = dict()

        self._op_list = list()
        hGates_cnt = 0
        for l in layers:
            out_var, op, in_var = parse_expr(l['expr'])
            if op != 'Concat':
                if op == 'gsm':
                    hGates_cnt += 1
                    id, out_name, module, out_channel, in_name = build_gsm(l,  self._channel_dict[in_var[0]],
                                                                                 conv_bias=True, num_segments=num_segments)

                    self._channel_dict[out_name] = out_channel
                    setattr(self, id, module)
                    self._op_list.append((id, op, out_name, in_name))
                elif op == 'attention':
                    hGates_cnt += 1
                    id, out_name, module, out_channel, in_name = build_attention(l,  self._channel_dict[in_var[0]],
                                                                                 conv_bias=True, attention_type=attention_type)

                    self._channel_dict[out_name] = out_channel
                    setattr(self, id, module)
                    self._op_list.append((id, op, out_name, in_name))
                else:
                    id, out_name, module, out_channel, in_name = get_basic_layer(l,
                                                                    3 if len(self._channel_dict) == 0 else self._channel_dict[in_var[0]],
                                                                                 conv_bias=True)

                    self._channel_dict[out_name] = out_channel
                    setattr(self, id, module)
                    self._op_list.append((id, op, out_name, in_name))
            else:
                self._op_list.append((id, op, out_var[0], in_var))
                channel = sum([self._channel_dict[x] for x in in_var])
                self._channel_dict[out_var[0]] = channel

        state_dict = torch.utils.model_zoo.load_url(weight_url)
        for k, v in state_dict.items():
            state_dict[k] = torch.squeeze(v, dim=0)
        self.load_state_dict(state_dict, strict=False)

    def forward(self, input):
        data_dict = dict()
        data_dict[self._op_list[0][-1]] = input

        def get_hook(name):

            def hook(m, grad_in, grad_out):
                print(name, grad_out[0].data.abs().mean())

            return hook
        for op in self._op_list:
            if op[1] != 'Concat' and op[1] != 'InnerProduct':
                data_dict[op[2]] = getattr(self, op[0])(data_dict[op[-1]])
                # getattr(self, op[0]).register_backward_hook(get_hook(op[0]))
            elif op[1] == 'InnerProduct':
                x = data_dict[op[-1]]
                data_dict[op[2]] = getattr(self, op[0])(x.view(x.size(0), -1))
            else:
                try:
                    data_dict[op[2]] = torch.cat(tuple(data_dict[x] for x in op[-1]), 1)
                except:
                    for x in op[-1]:
                        print(x,data_dict[x].size())
                    raise
        return data_dict[self._op_list[-1][2]]

class InceptionV3(BNInception):
    def __init__(self, model_path='model_zoo/bninception/inceptionv3.yaml', num_classes=101,
                 weight_url='https://yjxiong.blob.core.windows.net/models/inceptionv3-cuhk-0e09b300b493bc74c.pth'):
        super(InceptionV3, self).__init__(model_path=model_path, weight_url=weight_url, num_classes=num_classes)

class InceptionV3_gsm(BNInception_gsm):
    def __init__(self, model_path='model_zoo/bninception/inceptionv3_gsm.yaml', num_classes=101,
                 weight_url='https://yjxiong.blob.core.windows.net/models/inceptionv3-cuhk-0e09b300b493bc74c.pth',
                 num_segments=16):
        super(InceptionV3_gsm, self).__init__(model_path=model_path, weight_url=weight_url,
                                                        num_classes=num_classes, num_segments=num_segments)