# -*- encoding: utf-8 -*-
import os, sqlite3
import bottle
from lrprev import LRPrevFile

catalog = "./LR2MainCatalog-2.lrcat"
cache_dir = catalog[:-6] + " Previews.lrdata"

view = bottle.jinja2_view

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def sql(query, params=None, path=None):
    conn = sqlite3.connect(catalog if path is None else path)
    conn.row_factory = dict_factory
    c = conn.cursor()
    if params is None:
        c.execute(query)
    else:
        c.execute(query, params)
    data = c.fetchall()
    conn.rollback()  # we are read-only
    c.close()
    conn.close()
    return data

def get_cache_entries(photos):
    results = dict()
    conn = sqlite3.connect(os.path.join(cache_dir, "previews.db"))
    c = conn.cursor()
    for photo_id in photos:
        c.execute("select uuid, digest from ImageCacheEntry where imageId = ?", (photo_id,))
        row = c.fetchone()
        if row is not None:
            results[photo_id] = row
    c.close()
    conn.close()
    return results

def get_cache_entry(photo):
    res = get_cache_urls([photo])
    if len(res):
        return res[photo]
    else:
        return None

@bottle.route("/")
@bottle.route("/:year/")
@bottle.route("/:year/:month/")
@view("directory.html")
def index(year=None, month=None):
    if year is None:
        index = sql('''select substr(captureTime, 0, 5) as name, 
                              substr(captureTime, 0, 5) || '/' as url, 
                              count(*) as size 
                       from Adobe_images 
                       group by 1,2
                       order by 1''')
    elif month is None:
        index = sql('''select substr(captureTime, 0, 8) as name, 
                              substr(captureTime, 6, 2) || '/' as url, 
                              count(*) as size 
                       from Adobe_images 
                       where substr(captureTime, 0, 5) = :year 
                       group by 1,2
                       order by 1''', {'year': year})
    else:
        index = sql('''select substr(captureTime, 0, 11) as name, 
                              substr(captureTime, 9, 2) || '/' as url, 
                              count(*) as size 
                       from Adobe_images 
                       where substr(captureTime, 0, 8) = :month
                       group by 1,2
                       order by 1''', {'month': year + "-" + month})
    return locals()

@bottle.route("/:year/:month/:day/")
@view("thumbnails.html")
def day_thumbs(year, month, day):
    photos = sql('''select id_local, 
                           captureTime, 
                           colorLabels, 
                           fileHeight, 
                           fileWidth, 
                           pyramidIDCache, 
                           rating 
                    from Adobe_images 
                    where substr(captureTime, 0, 11) = :date
                    order by captureTime''', 
                        {'date': year + "-" + month + "-" + day})
    cache_entries = get_cache_entries([photo["id_local"] for photo in photos])
    for photo in photos:
        photo["img_src"] = "/cache/%s-%s/level_1" % cache_entries[photo["id_local"]]
        photo["url"] = "/cache/%s-%s/level_5" % cache_entries[photo["id_local"]]
    return locals()

@bottle.route("/cache/:uuid")
@bottle.route("/cache/:uuid/:level")
def load_from_cache(uuid, level=None):
    f = LRPrevFile(os.path.join(cache_dir, uuid[0], uuid[:4], uuid + ".lrprev"))
    if level is not None:
        data = f.load(level)
        f.close()
        if f.section_info(level)["kind"] == 0:
            bottle.response.content_type = "text/plain"
        else:
            bottle.response.content_type = "image/jpeg"
        return data
    else:
        res = "<html><body><ul>"
        for s in f.sections:
            res += '<li><a href="%s/%s">%s</a></li>' % (bottle.request.fullpath, s, s)
        res += "</ul></body></html>"
        return res

if __name__ == '__main__':
    bottle.debug(True)
    bottle.run(host='localhost', port=8001)
