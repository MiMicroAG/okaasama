import json
from pathlib import Path

p = Path(r"c:\Users\taxa\OneDrive\Develop\work\okaasama\お母様カレンダー\processed_files.json")
if not p.exists():
    print('no file')
    exit(0)

data = json.loads(p.read_text(encoding='utf-8'))
keys_to_remove = [k for k,v in data.items() if 'test_image_for_notify.jpg' in str(v.get('file_path',''))]
if not keys_to_remove:
    print('no entries to remove')
else:
    for k in keys_to_remove:
        del data[k]
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('removed', keys_to_remove)
