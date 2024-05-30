from flask import Flask, render_template, jsonify, send_from_directory, url_for, request
import time
from functools import partial
import os
import random
import argparse
import re
import threading
import magic
from copy import deepcopy 

def is_video (full_path) : 
    try:
        file_type = magic.from_file(full_path, mime=True)
        return file_type.startswith('video/')
    except:
        return False

def prepare_images (args): 
    image_paths = os.listdir(args.image_directory) 
    assert len(image_paths) > 0, f'There are no files in {args.image_directory}'

    # accumulate successful parses
    parsed = []
    for path in image_paths: 
        try :
            parsed.append((reverse_f_string(path, args.ip, int), path))
        except Exception : 
            continue

    assert len(parsed) > 0, f'(prepare_images) Did not find any file in directory that matches pattern {args.ip}' 

    # make image grid
    r_key = next(filter(lambda x : x.startswith('r:'), iter(parsed[0][0].keys())), None)
    c_key = next(filter(lambda x : x.startswith('c:'), iter(parsed[0][0].keys())), None)

    assert (r_key is not None) and (c_key is not None), f'Provided pattern ({args.ip}) does not have r: or c: prefixes'
    assert len(list(parsed[0][0].keys())) == 2, f'Found keys {list(parsed[0][0].keys())}'

    r_vals = sorted(list(set([_[0][r_key] for _ in parsed])))
    c_vals = sorted(list(set([_[0][c_key] for _ in parsed])))

    grid = [] 

    for r in r_vals : 
        row_items = [item for item in parsed if item[0][r_key] == r]
        grid.append([])
        for c in c_vals : 
            item = next(filter(lambda x: x[0][c_key] == c, row_items))
            grid[-1].append(item[1])
    
    result = { 'image_grid' : grid, 'column_vals': c_vals, 'row_vals': r_vals }

    # if row images are provided, consider them
    if args.rp is not None: 
        parsed = [] 
        for path in image_paths : 
            try :
                parsed.append((reverse_f_string(path, args.rp, int), path))
            except Exception :
                continue
        parsed = sorted(parsed, key=lambda x : next(iter(x[0].values())))
        row_image_paths = [b for a, b in parsed]
        result['row_image_paths'] = row_image_paths

    # if col images are provided, consider them
    if args.cp is not None: 
        parsed = [] 
        for path in image_paths : 
            try :
                parsed.append((reverse_f_string(path, args.cp, int), path))
            except Exception :
                continue
        parsed = sorted(parsed, key=lambda x : next(iter(x[0].values())))
        col_image_paths = [b for a, b in parsed]
        result['col_image_paths'] = col_image_paths

    return result

def reverse_f_string(s, fstring_pattern, var_types, scope=None):
    """
    Extracts variables from a string based on an f-string-like pattern. Optionally updates a provided scope with these variables.

    Parameters
    ----------
    s : str
        The string to be processed, which is expected to match the format defined by `fstring_pattern`.

    fstring_pattern : str
        The f-string-like pattern used to parse `s`. Variables in the pattern should be enclosed in curly braces, e.g., '{variable}'.

    var_types : type or list of types
        The type or a list of types to which the extracted string values should be converted. If a list is provided, it should be in the
        same order as the variables in `fstring_pattern`.

    scope : dict, optional
        The scope in which extracted variables should be updated. If provided, this function will update the scope with the extracted variables.
        If None (default), no scope is updated, and a dictionary of extracted variables is returned.

    Returns
    -------
    dict
        A dictionary containing the extracted variables and their values, converted to the specified types.

    Raises
    ------
    ValueError
        If the string `s` does not match the `fstring_pattern`, if the number of types provided does not match the number of variables,
        or if a type conversion fails.

    Example
    -------
    >>> values = reverse_f_string('epoch=0_step=4.ckpt', 'epoch={epoch}_step={step}.ckpt', [int, int], locals())
    >>> epoch, step = values['epoch'], values['step']
    >>> print(epoch, step)

    Notes
    -----
    - The function assumes that `fstring_pattern` contains simple variable placeholders and does not support complex expressions or format specifications.
    - When `scope` is provided, it must be a mutable dictionary-like object (e.g., the result of calling `locals()` or `globals()` in the calling scope).
    - The `var_types` parameter should either be a single type (if there's only one variable) or a list of types corresponding to each variable in order.
    """
    # Extract variable names from f-string-like pattern
    var_names = re.findall(r'\{(.*?)\}', fstring_pattern)

    # Validate and construct the regex pattern
    regex_pattern = fstring_pattern
    for var in var_names:
        regex_pattern = regex_pattern.replace(f"{{{var}}}", r"(.+?)")

    # Match against the string
    match = re.match(regex_pattern, s)
    if not match:
        raise ValueError(f'No match found - string {s}, pattern {regex_pattern}')

    # Ensure each variable name has exactly one match
    if len(match.groups()) != len(var_names):
        raise ValueError("Number of matches and variables do not correspond")

    # Convert parsed strings to specified types and return as a dict
    values = {}
    for i, var in enumerate(var_names):
        try:
            # Apply the type conversion
            var_type = var_types[i] if isinstance(var_types, list) else var_types
            value = var_type(match.group(i + 1))
            values[var] = value
        except ValueError as e:
            raise ValueError(f"Conversion error for variable '{var}': {e}")

    if scope is not None:
        scope.update(values)
    return values

app = Flask(__name__)

print(os.getcwd()) 
parser = argparse.ArgumentParser(description='Flask app serving images from a directory')
parser.add_argument('--image_directory', type=str, help='Path to the image directory', required=True)
parser.add_argument('--ip', required=True, help='Pattern for identifying images to show', type=str)
parser.add_argument('--rp', default=None, help='(Optional) Pattern for identifying row images', type=str)
parser.add_argument('--cp', default=None, help='(Optional) Pattern for identifying col images', type=str)
parser.add_argument('--sort_key', default=None, help='How to sort rows', type=str)
parser.add_argument('--port', default=7861, help='Port to run app on', type=int)
parser.add_argument('--host', default='0.0.0.0', help='Host to run app on', type=str)
args = parser.parse_args()

data = prepare_images(args)
image_data_lock = threading.Lock()

@app.route('/')
def index():
    data_ = deepcopy(data)
    data_['column_vals'] = ['', ''] + data_['column_vals']
    return render_template('index.html', data=data_)

@app.route('/load_more_images')
def load_more_images():
    with image_data_lock: 
        idx = request.args.get('row_id', type=int)
        try : 
            if args.cp is not None :
                if idx == 0 : 
                    images = [''] + data['col_image_paths'] 
                    params = [''] 
                else :
                    idx = idx - 1
                    images = [data['row_image_paths'][idx]] + data['image_grid'][idx]
                    params = [str(data['row_vals'][idx])]
            else :
                images = [data['row_image_paths'][idx]] + data['image_grid'][idx]
                params = [str(data['row_vals'][idx])]


            image_urls = [url_for('serve_image', filename=image) for image in images]
            return jsonify(params + [dict(src=a, video=is_video(b)) for a, b in zip(image_urls, images)])
            # params = ['\n'.join(f'{k}:{v}' for k, v in row_groups[0][idx][1].items())]
            # images = [group[idx][0] for group in row_groups]
            # image_urls = [url_for('serve_image', filename=image) for image in images]
            # return jsonify(params + [dict(src=a, video=is_video(b)) for a, b in zip(image_urls, images)])
        except IndexError :
            return jsonify([])

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(args.image_directory, filename)

def main() : 
    app.run(debug=True, port=args.port, host=args.host)

if __name__ == '__main__':
    main()

