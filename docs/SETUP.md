# Setting up the models

All four models are large and were run on **Google Colab with a GPU** during the project. The notebooks in `notebooks/` contain the
exact set-up cells that were used. In short:

## 1. Translation: IndicTrans (v1)
```bash
git clone https://github.com/AI4Bharat/indicTrans.git
git clone https://github.com/anoopkunchukuttan/indic_nlp_library.git
git clone https://github.com/anoopkunchukuttan/indic_nlp_resources.git
git clone https://github.com/rsennrich/subword-nmt.git
pip install sacremoses pandas mock sacrebleu tensorboardX pyarrow indic-nlp-library mosestokenizer subword-nmt
git clone https://github.com/pytorch/fairseq.git && pip install ./fairseq
wget https://ai4b-public-nlu-nlg.objectstore.e2enetworks.net/en2indic.zip && unzip en2indic.zip   # -> en-indic/
```
Run from inside `indicTrans/` (or add it and `fairseq` to `PYTHONPATH`), then use `Translator(expdir="../en-indic")`.
*fairseq is no longer maintained; if installation fails on a new Python, use Python 3.10 or migrate to IndicTrans2.*

## 2. Transliteration: IndicXlit
```bash
pip install ai4bharat-transliteration
```

## 3. Text-to-speech: IndicTTS
```bash
git clone https://github.com/AI4Bharat/Indic-TTS.git && cd Indic-TTS/inference
pip install TTS aksharamukha pyenchant nltk pysbd ...      # see notebooks/02_text_to_speech.ipynb
# checkpoints, one zip per language (hi, bn, mr, gu, kn, ta, te, ml):
wget https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/kn.zip && unzip kn.zip -d checkpoints
```
`Speaker(lang, checkpoints="checkpoints")` must be created from the `Indic-TTS/inference` folder (it imports `src.inference`).

## 4. Lip-sync video: Wav2Lip
```bash
git clone https://github.com/justinjohn0306/Wav2Lip
wget https://github.com/justinjohn0306/Wav2Lip/releases/download/models/wav2lip.pth -O Wav2Lip/checkpoints/wav2lip.pth
wget https://github.com/justinjohn0306/Wav2Lip/releases/download/models/wav2lip_gan.pth -O Wav2Lip/checkpoints/wav2lip_gan.pth
pip install ffmpeg-python mediapipe pydub moviepy batch-face
```
Supply a short, front-facing speaker video (≤ 720p works best). For subtitles in Indic scripts, install a matching font,
e.g. `apt-get install fonts-noto-core`.
