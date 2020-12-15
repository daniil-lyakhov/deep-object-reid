from subprocess import run
from pathlib import Path
from ruamel.yaml import YAML
import os
import argparse
import re
import numpy as np
import tempfile

def read_config(yaml: YAML, config_path: str):
    yaml.default_flow_style = True
    with open(config_path, 'r') as f:
        cfg = yaml.load(f)
    return cfg

def dump_config(yaml: YAML, config_path: str, cfg: dict):
    with open(config_path, 'w') as f:
        yaml.default_flow_style = True
        yaml.dump(cfg, f)

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_root', type=str, default='/home/prokofiev/datasets', required=False,
                        help='path to folder with datasets')
    args = parser.parse_args()

    path_to_main = '/home/prokofiev/deep-person-reid/scripts/main.py'
    data_root = args.data_root
    yaml = YAML()

    datasets = dict(
                    flowers = dict(resolution = (224,224), epochs = 50, source = 'classification', batch_size=64),
                    CIFAR100 = dict(resolution = (224,224), epochs = 200, source = 'classification_image_folder', batch_size=64),
                    fashionMNIST = dict(resolution = (28,28), epochs = 200, source = 'classification_image_folder', batch_size=512),
                    SVHN = dict(resolution = (32,32), epochs = 200, source = 'classification', batch_size=512),
                    cars = dict(resolution = (224,224), epochs = 50, source = 'classification', batch_size=64),
                    DTD = dict(resolution = (224,224), epochs = 60, source = 'classification_image_folder', batch_size=128),
                    pets = dict(resolution = (224,224), epochs = 35, source = 'classification', batch_size=128),
                    Xray = dict(resolution = (224,224), epochs = 70, source = 'classification_image_folder', batch_size=128),
                    SUN397 = dict(resolution = (224,224), epochs = 1, source = 'classification', batch_size=128),
                    birdsnap = dict(resolution = (224,224), epochs = 100, source = 'classification', batch_size=128),
                    caltech101 = dict(resolution = (224,224), epochs = 30, source = 'classification', batch_size=128),
                    FOOD101 = dict(resolution = (224,224), epochs = 40, source = 'classification', batch_size=128)
                    )

    path_to_base_cfg = str(Path.cwd() / 'configs'/ 'classification' / 'base_config_test.yml')
    to_skip = {'SUN397'}
    for key, params in datasets.items():
        if key in to_skip:
            continue
        cfg = read_config(yaml, path_to_base_cfg)
        num_exp = cfg['num_exp']
        if key in {'CIFAR100', 'FOOD101', 'pets', 'SUN397'}:
            cfg['train']['lr'] = 0.01
        elif key in {'DTD', 'Xray', 'birdsnap', 'caltech101', 'fashionMNIST'}:
            cfg['train']['lr'] = 0.016
        else:
            cfg['train']['lr'] = 0.02

        # create new configuration file related to current dataset
        # if key in ['CIFAR100_2', 'fashionMNIST', 'SVHN']:
        #     cfg['data']['transforms']['coarse_dropout']['max_holes'] = 3 if key == 'fashionMNIST' else 4
        #     cfg['data']['transforms']['coarse_dropout']['min_holes'] = 3 if key == 'fashionMNIST' else 4
        #     cfg['data']['transforms']['coarse_dropout']['max_height'] = 2
        #     cfg['data']['transforms']['coarse_dropout']['max_width'] = 2
        #     cfg['data']['transforms']['random_crop']['p'] = 1.0
        #     cfg['data']['transforms']['random_crop']['static'] = True

        cfg['model']['in_size'] = params['resolution']
        cfg['classification']['data_dir'] = key
        cfg['data']['height'] = params['resolution'][0]
        cfg['data']['width'] = params['resolution'][1]
        cfg['train']['max_epoch'] = params['epochs']
        cfg['train']['batch_size'] = params['batch_size']
        cfg['data']['save_dir'] = f"outputs/classification_out/exp_{num_exp}/{key}"
        source = params['source']
        cfg['data']['sources'] = [source]
        cfg['data']['targets'] = [source]
        # dump it
        # config_path = str(Path.cwd() / 'configs'/ 'classification' / f'{key}.yml')
        fd, tmp_path_to_cfg = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                # do stuff with temp file
                yaml.default_flow_style = True
                yaml.dump(cfg, tmp)
                tmp.close()

            # run training
            run(
                f'python {str(path_to_main)}'
                f' --config {tmp_path_to_cfg}'
                f' --root {data_root}', shell=True
                )
        finally:
            os.remove(tmp_path_to_cfg)

    # after training combine all outputs in one file
    path_to_bash = str(Path.cwd() / 'parse_output.sh')
    run(f'bash {path_to_bash} {num_exp}', shell=True)
    saver = dict()
    path_to_file = str(Path.cwd() / f"outputs/classification_out/exp_{num_exp}/combine_all.txt")
    # parse output file from bash script
    with open(path_to_file,'r') as f:
        for line in f:
            if line.strip() in datasets.keys():
                next_dataset = line.strip()
                saver[next_dataset] = dict()
                continue
            else:
                for metric in ['mAP', 'Rank-1', 'Rank-5']:
                    if line.strip().startswith(metric):
                        if not metric in saver[next_dataset]:
                            saver[next_dataset][metric] = []
                        pattern = re.search('\d+\.\d+', line.strip())
                        if pattern:
                            saver[next_dataset][metric].append(float(pattern.group(0)))

    # dump in appropriate patern
    names = ''; values = ''
    with open(path_to_file,'a') as f:
        for key in sorted(datasets.keys()):
            names += key + ' '
            if key in saver:
                best_top_1_idx = np.argmax(saver[key]['Rank-1'])
                top1 = str(saver[key]['Rank-1'][best_top_1_idx])
                mAP = str(saver[key]['mAP'][best_top_1_idx])
                top5 = str(saver[key]['Rank-5'][best_top_1_idx])
                snapshot = str(best_top_1_idx)
                values += mAP + ';' + top1 + ';' + top5 + ';' + snapshot + ';'
            else:
                values += '-1;-1;-1;-1;'

        f.write(f"\n{names}\n{values}")

if __name__ == "__main__":
    main()
