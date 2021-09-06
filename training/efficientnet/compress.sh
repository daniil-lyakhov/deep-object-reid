python /home/automation/dlyakhov/training_extensions/external/deep-object-reid/tools/main.py \
--config-file /home/automation/dlyakhov/training_extensions/external/deep-object-reid/training/efficientnet/EfficientNet_b0.yml \
--gpu-num 1 \
--custom-roots \
/home/automation/dlyakhov/training_extensions/external/deep-object-reid/CIFAR100/train \
/home/automation/dlyakhov/training_extensions/external/deep-object-reid/CIFAR100/val \
--root _ \
model.load_weights /mnt/icv_externalN/dlyakhov/ote-classification-checkpoint/CIFAR100_efficientnet/{name}.pth.tar-149 \
data.save_dir /home/automation/dlyakhov/training_extensions/external/deep-object-reid/training/efficientnet/output
