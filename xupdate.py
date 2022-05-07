from manga import start_craw
import fire


def main(web=''):
    with open("mangalist.txt", "r", encoding='utf-8') as tf:
        lines = tf.read().split('\n')

    count: int = 0
    tasks: list = []
    for jfile in lines:
        if web in jfile:
            count += 1
            tasks.append(jfile)

    print(f'{web} 总共：{len(tasks)}')
    for jfile in tasks:
        start_craw(jfile)


if __name__ == "__main__":
    fire.Fire(main)