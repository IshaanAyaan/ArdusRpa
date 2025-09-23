import argparse, json, asyncio
from dotenv import load_dotenv
from rpa.form_parser_gemini import build_config_from_gemini
from rpa.browser_filler import prefill_form
from rpa.types import FormConfig

def parse_args():
    p=argparse.ArgumentParser(description='Google Form RPA Agent (Gemini 2.5-flash + Playwright, no submit)')
    p.add_argument('--form', required=True)
    p.add_argument('--basic', default='basic_info.json')
    p.add_argument('--out', default='config.json')
    p.add_argument('--fill', action='store_true')
    p.add_argument('--headless', action='store_true')
    p.add_argument('--keep-open', action='store_true')
    p.add_argument('--fast', action='store_true', help='Block heavy resources to speed up page load')
    p.add_argument('--timeout-ms', type=int, default=5000, help='Default Playwright action timeout in ms (faster if lower)')
    return p.parse_args()

def main():
    load_dotenv()
    a=parse_args()
    basic=json.load(open(a.basic,'r',encoding='utf-8'))
    cfg=build_config_from_gemini(a.form, basic, 'prompts/mapping_prompt.md')
    fc=FormConfig.model_validate(cfg)
    open(a.out,'w',encoding='utf-8').write(json.dumps(fc.model_dump(), indent=2))
    print('📝 Wrote', a.out)
    if a.fill:
        asyncio.run(prefill_form(fc.model_dump(), headless=a.headless, keep_open=a.keep_open, fast=a.fast, default_timeout_ms=a.timeout_ms))
if __name__=='__main__':
    main()
