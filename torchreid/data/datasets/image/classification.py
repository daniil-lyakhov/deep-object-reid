from __future__ import absolute_import, division, print_function
import os
import os.path as osp
import numpy as np
from PIL import Image

from ..dataset import ImageDataset


class Classification(ImageDataset):
    """Classification dataset.
    """

    def __init__(self, root='', mode='train', dataset_id=0, load_masks=False, **kwargs):
        if load_masks:
            raise NotImplementedError

        self.root = osp.abspath(osp.expanduser(root))
        self.data_dir = osp.dirname(self.root)
        self.annot = self.root

        required_files = [
            self.data_dir, self.annot
        ]
        self.check_before_run(required_files)

        if mode == 'train':
            train = self.load_annotation(
                self.annot,
                self.data_dir,
                dataset_id=dataset_id
            )
        else:
            train = []

        if mode == 'query':
            query = self.load_annotation(
                self.annot,
                self.data_dir,
                dataset_id=dataset_id
            )
        else:
            query = []

        gallery = []

        super(Classification, self).__init__(train, query, gallery, mode=mode, **kwargs)

    @staticmethod
    def load_annotation(annot_path, data_dir, dataset_id=0):
        out_data = []
        for line in open(annot_path):
            parts = line.strip().split(' ')
            if len(parts) != 2:
                print("line doesn't fits pattern. Expected: 'relative_path/to/image label'")
                continue
            rel_image_path, label_str = parts
            full_image_path = osp.join(data_dir, rel_image_path)
            if not osp.exists(full_image_path):
                print(f"{full_image_path}: doesn't exist. Please check path or file")
                continue

            label = int(label_str)
            out_data.append((full_image_path, label, 0, dataset_id, '', -1, -1))
        return out_data


class ClassificationImageFolder(ImageDataset):
    """Classification dataset representing raw folders without annotation files.
    """

    def __init__(self, root='', mode='train', dataset_id=0, load_masks=False, filter_classes=None, **kwargs):
        if load_masks:
            raise NotImplementedError

        self.root = osp.abspath(osp.expanduser(root))

        required_files = [
            self.root
        ]
        self.check_before_run(required_files)

        if mode == 'train':
            train, classes = self.load_annotation(
                self.root, filter_classes, dataset_id
            )
            query = []
        elif mode == 'query':
            query, classes = self.load_annotation(
                self.root, filter_classes, dataset_id
            )
            train = []
        else:
            classes = []
            train, query = [], []

        gallery = []

        super().__init__(train, query, gallery, mode=mode, **kwargs)

        self.classes = classes


    @staticmethod
    def load_annotation(data_dir, filter_classes=None, dataset_id=0):
        ALLOWED_EXTS = ('.jpg', '.jpeg', '.png', '.gif')
        def is_valid(filename):
            return not filename.startswith('.') and filename.lower().endswith(ALLOWED_EXTS)

        def find_classes(dir, filter_names=None):
            if filter_names:
                classes = [d.name for d in os.scandir(dir) if d.is_dir() and d.name in filter_names]
            else:
                classes = [d.name for d in os.scandir(dir) if d.is_dir()]
            classes.sort()
            class_to_idx = {classes[i]: i for i in range(len(classes))}
            return class_to_idx

        class_to_idx = find_classes(data_dir, filter_classes)

        out_data = []
        for target_class in sorted(class_to_idx.keys()):
            class_index = class_to_idx[target_class]
            target_dir = osp.join(data_dir, target_class)
            if not osp.isdir(target_dir):
                continue
            for root, _, fnames in sorted(os.walk(target_dir, followlinks=True)):
                for fname in sorted(fnames):
                    path = osp.join(root, fname)
                    if is_valid(path):
                        out_data.append((path, class_index, 0, dataset_id, '', -1, -1))\

        if not len(out_data):
            print('Failed to locate images in folder ' + data_dir + f' with extensions {ALLOWED_EXTS}')

        return out_data, class_to_idx


class ClassificationNOUS(ImageDataset):
    """
    Dataloader that generates logits from DatasetItems.
    """
    def __init__(self, root='', mode='train', inference_mode=False, dataset_id=0,
                 load_masks=False, filter_classes=None, transforms=None, **kwargs):

        self.dataset, self.labels = root
        self.inference_mode = inference_mode

        if mode == 'train':
            train, classes = self.load_annotation(
                self.dataset, self.labels, dataset_id
            )
            query = []
        elif mode == 'query':
            query, classes = self.load_annotation(
                self.dataset, self.labels, dataset_id
            )
            train = []
        else:
            classes = []
            train, query = [], []

        gallery = []

        super().__init__(train, query, gallery, mode=mode, **kwargs)

        self.classes = classes

    @staticmethod
    def load_annotation(dataset, labels, dataset_id=0):
        class_to_idx = {i : label for i, label in enumerate(labels)}

        out_data = []
        for item in dataset:
            label = item.annotation.get_labels()[0]
            out_data.append((' ', label, 0, dataset_id, '', -1, -1))

        return out_data, class_to_idx

    def __len__(self):
        return len(self.dataset)

    def get_input(self, idx: int):
        """
        Return the centered and scaled input tensor for file with 'idx'
        """
        sample = self.dataset[idx].numpy  # This returns 8-bit numpy array of shape (height, width, RGB)

        if self.transform is not None:
            img = Image.fromarray(sample)
            img, _ = self.transform((img, ''))
        return img

    def __getitem__(self, idx: int):
        """
        Return the input and the an optional encoded target for training with index 'idx'
        """
        input_image = self.get_input(idx)

        if self.inference_mode:
            class_num = np.asarray(0)
        else:
            item = self.dataset[idx]
            if len(item.annotation.get_labels()) == 0:
                raise ValueError(
                    f"No labels in annotation found. Annotation: {item.annotation}")
            label = item.annotation.get_labels()[0]
            class_num = self.labels.index(label)
            class_num = np.asarray(class_num)
        return input_image, class_num, 0
