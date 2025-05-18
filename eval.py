import evaluating.generate
import evaluating.score
import asyncio
import sys


async def run():
    if len(sys.argv) < 4:
        print("""
usage:
python eval.py {command} {model_name} {take}
command - score|generate - action, expected to run to processes score & generate in parallel
model_name - original for original deepseek model, or ./data/{model_name} local model path
take - eval size
""")
        return

    command = sys.argv[1]
    name = sys.argv[2]
    take = int(sys.argv[3])

    no_fixing = False
    if len(sys.argv) >= 5 and sys.argv[4] == '--no-fixing':
        no_fixing = True

    if command == 'generate':
        await evaluating.generate.generate(name, take, no_fixing)
        return

    if command == 'score':
        await evaluating.score.score(name, take, no_fixing)
        return
    
    print('first argument must be "generate" or "score"')

if __name__ == '__main__':
    asyncio.run(run())
