from __future__ import division, print_function, absolute_import

import copy
import os.path as osp
from collections import defaultdict

import numpy as np
import tarfile
import zipfile
import torch

from torchreid.utils import read_image, download_url, mkdir_if_missing


class Dataset:
    """An abstract class representing a Dataset.

    This is the base class for ``ImageDataset`` and ``VideoDataset``.

    Args:
        train (list): contains tuples of (img_path(s), pid, camid).
        query (list): contains tuples of (img_path(s), pid, camid).
        gallery (list): contains tuples of (img_path(s), pid, camid).
        transform: transform function.
        mode (str): 'train', 'query' or 'gallery'.
        combineall (bool): combines train, query and gallery in a dataset for training.
        verbose (bool): show information.
    """
    _junk_pids = []  # contains useless person IDs, e.g. background, false detections

    def __init__(
        self,
        train,
        query,
        gallery,
        transform=None,
        mode='train',
        combineall=False,
        verbose=True,
        **kwargs
    ):
        self.train = train
        self.query = query
        self.gallery = gallery
        self.transform = transform
        self.mode = mode
        self.combineall = combineall
        self.verbose = verbose

        self.num_train_pids = self.get_num_pids(self.train)
        self.num_train_cams = self.get_num_cams(self.train)
        self.data_counts = self.get_data_counts(self.train)

        if self.combineall:
            self.combine_all()

        if self.mode == 'train':
            self.data = self.train
        elif self.mode == 'query':
            self.data = self.query
        elif self.mode == 'gallery':
            self.data = self.gallery
        else:
            raise ValueError('Invalid mode. Got {}, but expected to be '
                             'one of [train | query | gallery]'.format(self.mode))

        if self.verbose:
            self.show_summary()

    def __getitem__(self, index):
        raise NotImplementedError

    def __len__(self):
        return len(self.data)

    def __add__(self, other):
        """Adds two datasets together (only the train set)."""
        updated_train = copy.deepcopy(self.train)

        for record in other.train:
            dataset_id = record['dataset_id'] if isinstance(record, dict) else 0

            num_train_pids = 0
            if dataset_id in self.num_train_pids:
                num_train_pids = self.num_train_pids[dataset_id]
            old_obj_id = record['obj_id'] if isinstance(record, dict) else record[1]
            new_obj_id = old_obj_id + num_train_pids

            num_train_cams = 0
            if dataset_id in self.num_train_cams:
                num_train_cams = self.num_train_cams[dataset_id]
            old_cam_id = record['cam_id'] if isinstance(record, dict) else record[2]
            new_cam_id = old_cam_id + num_train_cams

            if isinstance(record, dict):
                record['obj_id'] = new_obj_id
                record['cam_id'] = new_cam_id
                updated_record = record
            else:
                updated_record = tuple([record[0], new_obj_id, new_cam_id] + list(record[3:]))

            updated_train.append(updated_record)

        ###################################
        # Things to do beforehand:
        # 1. set verbose=False to avoid unnecessary print
        # 2. set combineall=False because combineall would have been applied
        #    if it was True for a specific dataset, setting it to True will
        #    create new IDs that should have been included
        ###################################

        first_field = updated_train[0]['img_path'] if isinstance(updated_train[0], dict) else updated_train[0][0]
        if isinstance(first_field, str):
            return ImageDataset(
                updated_train,
                self.query,
                self.gallery,
                transform=self.transform,
                mode=self.mode,
                combineall=False,
                verbose=False
            )
        else:
            return VideoDataset(
                updated_train,
                self.query,
                self.gallery,
                transform=self.transform,
                mode=self.mode,
                combineall=False,
                verbose=False,
                seq_len=self.seq_len,
                sample_method=self.sample_method
            )

    def __radd__(self, other):
        """Supports sum([dataset1, dataset2, dataset3])."""
        if other == 0:
            return self
        else:
            return self.__add__(other)

    @staticmethod
    def parse_data(data):
        """Parses data list and returns the number of person IDs
        and the number of camera views.

        Args:
            data (list): contains tuples of (img_path(s), pid, camid)
        """

        pids, cams = defaultdict(set), defaultdict(set)
        for record in data:
            dataset_id = record['dataset_id'] if isinstance(record, dict) else 0
            pids[dataset_id].add(record['obj_id'] if isinstance(record, dict) else record[1])
            cams[dataset_id].add(record['cam_id'] if isinstance(record, dict) else record[2])

        num_pids = {dataset_id: len(dataset_pids) for dataset_id, dataset_pids in pids.items()}
        num_cams = {dataset_id: len(dataset_cams) for dataset_id, dataset_cams in cams.items()}

        return num_pids, num_cams

    def get_num_pids(self, data):
        """Returns the number of training person identities."""
        return self.parse_data(data)[0]

    def get_num_cams(self, data):
        """Returns the number of training cameras."""
        return self.parse_data(data)[1]

    @staticmethod
    def get_data_counts(data):
        counts = dict()
        for record in data:
            dataset_id = record['dataset_id'] if isinstance(record, dict) else 0
            if dataset_id not in counts:
                counts[dataset_id] = defaultdict(int)

            obj_id = record['obj_id'] if isinstance(record, dict) else record[1]
            counts[dataset_id][obj_id] += 1

        return counts

    def show_summary(self):
        """Shows dataset statistics."""
        pass

    @staticmethod
    def _get_obj_ids(data, junk_obj_ids, obj_ids=None):
        if obj_ids is None:
            obj_ids = defaultdict(set)

        for record in data:
            obj_id = record['obj_id'] if isinstance(record, dict) else record[1]
            if obj_id in junk_obj_ids:
                continue

            dataset_id = record['dataset_id'] if isinstance(record, dict) else 0
            obj_ids[dataset_id].add(record['obj_id'] if isinstance(record, dict) else record[1])

        return obj_ids

    @staticmethod
    def _relabel(data, junk_obj_ids, id2label_map, num_train_ids):
        out_data = []
        for record in data:
            obj_id = record['obj_id'] if isinstance(record, dict) else record[1]
            if obj_id in junk_obj_ids:
                continue

            dataset_id = record['dataset_id'] if isinstance(record, dict) else 0
            obj_id = id2label_map[dataset_id][obj_id] + num_train_ids[dataset_id]

            if isinstance(data[0], dict):
                out_record = copy.deepcopy(record)
                out_record['obj_id'] = obj_id
            else:
                out_record = record[:1] + (obj_id,) + record[2:]

            out_data.append(out_record)

        return out_data

    def combine_all(self):
        """Combines train, query and gallery in a dataset for training."""
        combined = copy.deepcopy(self.train)

        new_obj_ids = self._get_obj_ids(self.query, self._junk_pids)
        new_obj_ids = self._get_obj_ids(self.gallery, self._junk_pids, new_obj_ids)

        id2label_map = dict()
        for dataset_id, dataset_ids in new_obj_ids.items():
            id2label_map[dataset_id] = {obj_id: i for i, obj_id in enumerate(set(dataset_ids))}

        combined += self._relabel(self.query, self._junk_pids, id2label_map, self.num_train_pids)
        combined += self._relabel(self.gallery, self._junk_pids, id2label_map, self.num_train_pids)

        self.train = combined
        self.num_train_pids = self.get_num_pids(self.train)

    def download_dataset(self, dataset_dir, dataset_url):
        """Downloads and extracts dataset.

        Args:
            dataset_dir (str): dataset directory.
            dataset_url (str): url to download dataset.
        """
        if osp.exists(dataset_dir):
            return

        if dataset_url is None:
            raise RuntimeError(
                '{} dataset needs to be manually '
                'prepared, please follow the '
                'document to prepare this dataset'.format(
                    self.__class__.__name__
                )
            )

        print('Creating directory "{}"'.format(dataset_dir))
        mkdir_if_missing(dataset_dir)
        fpath = osp.join(dataset_dir, osp.basename(dataset_url))

        print(
            'Downloading {} dataset to "{}"'.format(
                self.__class__.__name__, dataset_dir
            )
        )
        download_url(dataset_url, fpath)

        print('Extracting "{}"'.format(fpath))
        try:
            tar = tarfile.open(fpath)
            tar.extractall(path=dataset_dir)
            tar.close()
        except:
            zip_ref = zipfile.ZipFile(fpath, 'r')
            zip_ref.extractall(dataset_dir)
            zip_ref.close()

        print('{} dataset is ready'.format(self.__class__.__name__))

    @staticmethod
    def check_before_run(required_files):
        """Checks if required files exist before going deeper.

        Args:
            required_files (str or list): string file name(s).
        """
        if isinstance(required_files, str):
            required_files = [required_files]

        for fpath in required_files:
            if not osp.exists(fpath):
                raise RuntimeError('"{}" is not found'.format(fpath))

    @staticmethod
    def _compress_labels(data):
        if len(data) == 0:
            return data

        pid_container = set(record['obj_id'] if isinstance(record, dict) else record[1] for record in data)
        pid2label = {pid: label for label, pid in enumerate(pid_container)}

        if isinstance(data[0], dict):
            out_data = data
            for record in out_data:
                record['obj_id'] = pid2label[record['obj_id']]
        else:
            out_data = [record[:1] + (pid2label[record[1]],) + record[2:] for record in data]

        return out_data

    def __repr__(self):
        num_train_pids, num_train_cams = self.parse_data(self.train)
        num_query_pids, num_query_cams = self.parse_data(self.query)
        num_gallery_pids, num_gallery_cams = self.parse_data(self.gallery)

        msg = '  ----------------------------------------\n' \
              '  subset   | # ids | # items | # cameras\n' \
              '  ----------------------------------------\n' \
              '  train    | {:5d} | {:7d} | {:9d}\n' \
              '  query    | {:5d} | {:7d} | {:9d}\n' \
              '  gallery  | {:5d} | {:7d} | {:9d}\n' \
              '  ----------------------------------------\n' \
              '  items: images/tracklets for image/video dataset\n'.format(
                  sum(num_train_pids.values()), len(self.train), sum(num_train_cams.values()),
                  sum(num_query_pids.values()), len(self.query), sum(num_query_cams.values()),
                  sum(num_gallery_pids.values()), len(self.gallery), sum(num_gallery_cams.values())
              )

        return msg


class ImageDataset(Dataset):
    """A base class representing ImageDataset.

    All other image datasets should subclass it.

    ``__getitem__`` returns an image given index.
    It will return ``img``, ``pid``, ``camid`` and ``img_path``
    where ``img`` has shape (channel, height, width). As a result,
    data in each batch has shape (batch_size, channel, height, width).
    """

    def __init__(self, train, query, gallery, **kwargs):
        super(ImageDataset, self).__init__(train, query, gallery, **kwargs)

    def __getitem__(self, index):
        input_record = self.data[index]

        if isinstance(input_record, dict):
            output_record = input_record

            image = read_image(input_record['img_path'], grayscale=False)
            mask = read_image(input_record['mask_path'], grayscale=True) if 'mask_path' in input_record else ''

            if self.transform is not None:
                image, mask = self.transform((image, mask))

            output_record['img'] = image
            if mask != '':
                output_record['mask'] = mask
        else:
            pid = input_record[1]
            cam_id = input_record[2]

            image = read_image(input_record[0], grayscale=False)
            if self.transform is not None:
                image, _ = self.transform((image, ''))

            output_record = image, pid, cam_id

        return output_record

    def show_summary(self):
        num_train_pids, num_train_cams = self.parse_data(self.train)
        num_query_pids, num_query_cams = self.parse_data(self.query)
        num_gallery_pids, num_gallery_cams = self.parse_data(self.gallery)

        print('=> Loaded {}'.format(self.__class__.__name__))
        print('  ----------------------------------------')
        print('  subset   | # ids | # images | # cameras')
        print('  ----------------------------------------')
        print('  train    | {:5d} | {:8d} | {:9d}'.format(
            sum(num_train_pids.values()), len(self.train), sum(num_train_cams.values())))
        print('  query    | {:5d} | {:8d} | {:9d}'.format(
            sum(num_query_pids.values()), len(self.query), sum(num_query_cams.values())))
        print('  gallery  | {:5d} | {:8d} | {:9d}'.format(
            sum(num_gallery_pids.values()), len(self.gallery), sum(num_gallery_cams.values())))
        print('  ----------------------------------------')


class VideoDataset(Dataset):
    """A base class representing VideoDataset.

    All other video datasets should subclass it.

    ``__getitem__`` returns an image given index.
    It will return ``imgs``, ``pid`` and ``camid``
    where ``imgs`` has shape (seq_len, channel, height, width). As a result,
    data in each batch has shape (batch_size, seq_len, channel, height, width).
    """

    def __init__(
        self,
        train,
        query,
        gallery,
        seq_len=15,
        sample_method='evenly',
        **kwargs
    ):
        super(VideoDataset, self).__init__(train, query, gallery, **kwargs)
        self.seq_len = seq_len
        self.sample_method = sample_method

        if self.transform is None:
            raise RuntimeError('transform must not be None')

    def __getitem__(self, index):
        img_paths, pid, camid = self.data[index]
        num_imgs = len(img_paths)

        if self.sample_method == 'random':
            # Randomly samples seq_len images from a tracklet of length num_imgs,
            # if num_imgs is smaller than seq_len, then replicates images
            indices = np.arange(num_imgs)
            replace = False if num_imgs >= self.seq_len else True
            indices = np.random.choice(
                indices, size=self.seq_len, replace=replace
            )
            # sort indices to keep temporal order (comment it to be order-agnostic)
            indices = np.sort(indices)

        elif self.sample_method == 'evenly':
            # Evenly samples seq_len images from a tracklet
            if num_imgs >= self.seq_len:
                num_imgs -= num_imgs % self.seq_len
                indices = np.arange(0, num_imgs, num_imgs / self.seq_len)
            else:
                # if num_imgs is smaller than seq_len, simply replicate the last image
                # until the seq_len requirement is satisfied
                indices = np.arange(0, num_imgs)
                num_pads = self.seq_len - num_imgs
                indices = np.concatenate(
                    [
                        indices,
                        np.ones(num_pads).astype(np.int32) * (num_imgs-1)
                    ]
                )
            assert len(indices) == self.seq_len

        elif self.sample_method == 'all':
            # Samples all images in a tracklet. batch_size must be set to 1
            indices = np.arange(num_imgs)

        else:
            raise ValueError(
                'Unknown sample method: {}'.format(self.sample_method)
            )

        imgs = []
        for index in indices:
            img_path = img_paths[int(index)]
            img = read_image(img_path)
            if self.transform is not None:
                img = self.transform(img)
            img = img.unsqueeze(0) # img must be torch.Tensor
            imgs.append(img)
        imgs = torch.cat(imgs, dim=0)

        return imgs, pid, camid

    def show_summary(self):
        num_train_pids, num_train_cams = self.parse_data(self.train)
        num_query_pids, num_query_cams = self.parse_data(self.query)
        num_gallery_pids, num_gallery_cams = self.parse_data(self.gallery)

        print('=> Loaded {}'.format(self.__class__.__name__))
        print('  -------------------------------------------')
        print('  subset   | # ids | # tracklets | # cameras')
        print('  -------------------------------------------')
        print(
            '  train    | {:5d} | {:11d} | {:9d}'.format(
                num_train_pids, len(self.train), num_train_cams
            )
        )
        print(
            '  query    | {:5d} | {:11d} | {:9d}'.format(
                num_query_pids, len(self.query), num_query_cams
            )
        )
        print(
            '  gallery  | {:5d} | {:11d} | {:9d}'.format(
                num_gallery_pids, len(self.gallery), num_gallery_cams
            )
        )
        print('  -------------------------------------------')
