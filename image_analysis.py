"""Local BioCLIP image-to-candidate matching for BushSignal.

Uploaded images stay on this machine. Scores rank the supplied species
candidates and are not calibrated identification confidence.
"""

from functools import lru_cache
import os
from pathlib import Path

os.environ["HF_HOME"] = str(Path(__file__).parent / ".cache" / "huggingface")

MODEL_ID = "imageomics/bioclip"
MODEL_REF = f"hf-hub:{MODEL_ID}"


@lru_cache(maxsize=1)
def _load_model():
    cache_root = Path(os.environ["HF_HOME"]) / "hub" / "models--imageomics--bioclip" / "snapshots"
    cached_checkpoint = any(
        (snapshot / "open_clip_config.json").is_file()
        and (snapshot / "open_clip_pytorch_model.bin").is_file()
        and (snapshot / "open_clip_pytorch_model.bin").stat().st_size > 0
        for snapshot in cache_root.glob("*")
    ) if cache_root.exists() else False
    if cached_checkpoint:
        # Avoid unnecessary Hub requests on subsequent local app launches.
        os.environ["HF_HUB_OFFLINE"] = "1"

    import open_clip
    import torch

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_REF)
    tokenizer = open_clip.get_tokenizer(MODEL_REF)
    model.eval()
    return torch, model, preprocess, tokenizer


def analyze_image(image, candidate_labels, top_k=5):
    """Rank user-supplied organism names against a PIL image using BioCLIP."""
    labels = list(dict.fromkeys(str(label).strip() for label in candidate_labels if str(label).strip()))
    if not labels:
        raise ValueError("Enter at least one species name to compare against the image.")

    torch, model, preprocess, tokenizer = _load_model()
    image_tensor = preprocess(image.convert("RGB")).unsqueeze(0)
    text = tokenizer([f"a photo of {label}" for label in labels])
    with torch.inference_mode():
        image_features = model.encode_image(image_tensor)
        text_features = model.encode_text(text)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarities = (image_features @ text_features.T).squeeze(0)
        scores, indices = torch.topk(similarities, k=min(top_k, len(labels)))

    return [
        {"label": labels[index], "score": float(score)}
        for score, index in zip(scores.tolist(), indices.tolist())
    ]
