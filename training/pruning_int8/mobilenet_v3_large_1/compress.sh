python /home/automation/dlyakhov/training_extensions/external/deep-object-reid/tools/main.py \
--config-file /home/automation/dlyakhov/training_extensions/external/deep-object-reid/training/pruning_int8/mobilenet_v3_large_1/mobilenetv3_large.yml \
--gpu-num 1 \
--custom-roots \
/home/automation/dlyakhov/training_extensions/external/deep-object-reid/CIFAR100/train \
/home/automation/dlyakhov/training_extensions/external/deep-object-reid/CIFAR100/val \
--root _ \
model.load_weights /mnt/icv_externalN/dlyakhov/ote-classification-checkpoint/CIFAR100_mobielenet_v3_large/model_0/{name}.pth.tar-113 \
data.save_dir /home/automation/dlyakhov/training_extensions/external/deep-object-reid/training/pruning_int8/mobilenet_v3_large_1/output_21_09
