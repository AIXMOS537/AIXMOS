#!/usr/bin/env python
"""Lightweight mentorship CLI

Commands:
  --list                 : list available lessons and resources
  --show <id>            : show lesson by filename
  --plan                 : show the 90-day mentorship plan
  --prompt [master|daily|codex] : print a mentorship prompt template
  --chat <prompt>        : call OpenAI if OPENAI_API_KEY set (optional)
  --codex <task>         : call low-token Codex-style prompt if OPENAI_API_KEY set

"""
import argparse
import os
import sys

BASE = os.path.dirname(__file__)
LESSONS_DIR = os.path.join(BASE, "lessons")
PROMPTS_DIR = os.path.join(BASE, "prompts")
PLAN_FILE = os.path.join(BASE, "90_day_plan.md")


def list_lessons():
    items = sorted([f for f in os.listdir(LESSONS_DIR) if f.endswith('.md')])
    print("Lessons:")
    for f in items:
        print(f)
    if os.path.exists(PLAN_FILE):
        print("\n90-day plan: 90_day_plan.md")
    print("\nPrompt templates:")
    for f in sorted([f for f in os.listdir(PROMPTS_DIR) if f.endswith('.md')]):
        print(f)


def show_lesson(name):
    path = os.path.join(LESSONS_DIR, name)
    if not os.path.exists(path):
        candidates = [f for f in os.listdir(LESSONS_DIR) if name in f]
        if not candidates:
            print('Lesson not found')
            return
        path = os.path.join(LESSONS_DIR, candidates[0])
    print(open(path, 'r', encoding='utf-8').read())


def print_plan():
    if not os.path.exists(PLAN_FILE):
        print('90-day plan not found.')
        return
    print(open(PLAN_FILE, 'r', encoding='utf-8').read())


def print_prompt(prompt_name='master'):
    prompt_map = {
        'master': 'MASTER_MENTOR_PROMPT.md',
        'daily': 'DAILY_MENTOR_PROMPT.md',
        'codex': 'LOW_TOKEN_CODEX_PROMPT.md',
    }
    prompt_file = prompt_map.get(prompt_name, 'MASTER_MENTOR_PROMPT.md')
    path = os.path.join(PROMPTS_DIR, prompt_file)
    if not os.path.exists(path):
        print(f'Prompt template not found: {prompt_file}')
        return
    print(open(path, 'r', encoding='utf-8').read())


def call_openai(prompt_text, model=None):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        print('OPENAI_API_KEY not set. Set it to enable chat calls.')
        return
    try:
        import openai
        openai.api_key = key
        m = model or os.environ.get('OPENAI_MODEL','gpt-4o-mini')
        resp = openai.ChatCompletion.create(model=m, messages=[{'role':'user','content':prompt_text}])
        print(resp['choices'][0]['message']['content'])
    except Exception as e:
        print('OpenAI call failed:', e)


def call_codex(task_text, model=None):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        print('OPENAI_API_KEY not set. Set it to enable chat calls.')
        return
    template_path = os.path.join(PROMPTS_DIR, 'LOW_TOKEN_CODEX_PROMPT.md')
    if not os.path.exists(template_path):
        print('Codex prompt template not found.')
        return
    template = open(template_path, 'r', encoding='utf-8').read()
    prompt_text = template.replace('{TASK}', task_text)
    try:
        import openai
        openai.api_key = key
        m = model or os.environ.get('OPENAI_MODEL','gpt-4o-mini')
        resp = openai.ChatCompletion.create(model=m, messages=[{'role':'user','content':prompt_text}])
        print(resp['choices'][0]['message']['content'])
    except Exception as e:
        print('OpenAI call failed:', e)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', action='store_true')
    p.add_argument('--show')
    p.add_argument('--plan', action='store_true')
    p.add_argument('--prompt', nargs='?', const='master', choices=['master', 'daily', 'codex'])
    p.add_argument('--chat')
    p.add_argument('--codex')
    p.add_argument('--model')
    args = p.parse_args()

    if args.list:
        list_lessons()
        return
    if args.show:
        show_lesson(args.show)
        return
    if args.plan:
        print_plan()
        return
    if args.prompt:
        print_prompt(args.prompt)
        return
    if args.chat:
        call_openai(args.chat, model=args.model)
        return
    if args.codex:
        call_codex(args.codex, model=args.model)
        return
    p.print_help()


if __name__ == '__main__':
    main()
