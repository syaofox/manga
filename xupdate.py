from manga import start_craw
import fire



def main(web='all'):
    with open("mangalist.txt", "r", encoding='utf-8') as tf:
        lines = tf.read().split('\n')

    list_18comic = []
    list_manhuagui = []
    list_raw = []
    list_all = []

    for jfile in lines:
        list_all.append(jfile)
        if jfile.endswith('18comic.json'):
            list_18comic.append(jfile)

        elif jfile.endswith('manhuagui.json'):
            list_manhuagui.append(jfile)

        else:
            list_raw.append(jfile)

    match web:
        case "18comic":
            print(f'总共：{len(list_18comic)}')
            for jfile in list_18comic:
                start_craw(jfile)
        case "manhuagui":
            print(f'总共：{len(list_manhuagui)}')
            for jfile in list_manhuagui:
                start_craw(jfile)
        case "raw":
            print(f'总共：{len(list_raw)}')
            for jfile in list_raw:
                start_craw(jfile)

        case "all":
            print(f'总共：{len(list_all)}')
            for jfile in list_all:
                start_craw(jfile)

    


if __name__ == "__main__":
    fire.Fire(main)