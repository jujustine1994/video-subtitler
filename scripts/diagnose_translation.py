"""Inspect translation status metadata only, never emit source/translation text."""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dotenv import dotenv_values
from src import resume, translator
from src.groq_provider import GroqProvider


def main():
    p = argparse.ArgumentParser()
    p.add_argument('source')
    p.add_argument('--index',default='0')
    p.add_argument('--count',type=int)
    args = p.parse_args()
    project = Path(__file__).resolve().parent.parent
    identity = GroqProvider('unused','whisper-large-v3',language='ja').identity
    state = json.loads(resume.checkpoint_path(args.source,identity).read_text(encoding='utf8'))
    cues = state['transcripts'][args.index]
    if args.count:
        cues = cues[:args.count]
    client = translator.make_client(dotenv_values(project/'.env')['GEMINI_API_KEY'])
    class Models:
        def generate_content(self, **kwargs):
            response = client.models.generate_content(**kwargs)
            print(json.dumps({'cues':len(cues),
                              'finish_reasons':[str(c.finish_reason) for c in response.candidates or []],
                              'block_reason':str(getattr(response.prompt_feedback,'block_reason',None)),
                              'text_chars':len(response.text or '')}),flush=True)
            (project/'validation_outputs'/'translation-diagnostic.json').write_text(
                response.model_dump_json(),encoding='utf8')
            return response
    try:
        result = translator._translate_cues(SimpleNamespace(models=Models()),cues,
                                            translator.prompts.DEFAULT_TARGET_LANGUAGE)
        print(json.dumps({'translation_valid':True,'count':len(result)}),flush=True)
    except Exception as exc:
        print(json.dumps({'translation_valid':False,'error':translator._safe_err(exc)}),flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
