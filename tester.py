from trainer.ae.build_dataset import build_ae_training_set

data = build_ae_training_set(max_percentile=85)

print(data["X_train"].shape)
print(data["stats"])
