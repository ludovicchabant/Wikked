import os
import os.path
import argparse
from sqlalchemy import create_engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('-o', '--out', default='wikked_import')
    parser.add_argument('--prefix', default='wiki')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--ext', default='.md')
    args = parser.parse_args()

    prefix = args.prefix
    out_dir = args.out
    ext = '.' + args.ext.lstrip('.')

    if not out_dir:
        parser.print_help()
        return 1

    if os.path.isdir(out_dir):
        print("The output directory already exists!")
        return 1

    engine = create_engine(args.url, echo=args.verbose)
    conn = engine.connect()

    query = (
        'SELECT '
        'p.page_id,p.page_title,p.page_latest,'
        'r.rev_id,r.rev_text_id,t.old_id,t.old_text '
        'from %(prefix)s_page p '
        'INNER JOIN %(prefix)s_revision r ON p.page_latest = r.rev_id '
        'INNER JOIN %(prefix)s_text t ON r.rev_text_id = t.old_id;' %
        {'prefix': prefix})
    q = conn.execute(query)
    for p in q:
        title = p['page_title'].decode('utf8')
        text = p['old_text'].decode('utf8')

        path_noext = os.path.join(out_dir, title)
        path = path_noext + ext
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        if os.path.exists(path):
            suffnum = 2
            while True:
                new_path = '%s_%d%s' % (path_noext, suffnum, ext)
                if not os.path.exists(new_path):
                    break
                suffnum += 1
                if suffnum > 100:
                    raise Exception("Can't find available path for: " %
                                    path)

            print("WARNING: %s exists" % path)
            print("WARNING: creating %s instead" % new_path)
            path = new_path

        print(p['page_id'], title)
        with open(path, 'w', encoding='utf8') as fp:
            fp.write(text)

    conn.close()


if __name__ == '__main__':
    main()
