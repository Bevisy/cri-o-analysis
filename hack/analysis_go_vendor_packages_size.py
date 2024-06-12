#!/usr/bin/env python3

# Copyright @Bevisy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import os
import argparse
import logging
import subprocess

# collect go packages from go.mod
def get_dependencies():
    if not os.path.exists('go.mod'):
        raise FileNotFoundError("go.mod file does not exist")
    with open('go.mod', 'r') as file:
        lines = file.readlines()
    dependencies = []
    start_collecting = False
    for line in lines:
        if line.startswith('require ('):
            start_collecting = True
            continue
        if line.startswith(')'):
            start_collecting = False
        if start_collecting:
            dependencies.append(line.split()[0])
    return dependencies

# return -1 if no go files found, 0 for other error
def compile_and_get_size(package):
    if not os.path.exists('vendor'):
        raise FileNotFoundError("vendor directory does not exist. Please run 'go mod vendor' to generate it.")
    
    # add ./vendor/ prefix if not exists
    if not package.startswith('./vendor/'):
        package_path = f"./vendor/{package}"
    else:
        package_path = package

    # build go package from the given package path
    result = subprocess.run(['go', 'build', '--gcflags', 'all=-N -L', '-o', f'{package_path}.a', package_path], 
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if "no Go files" in result.stdout:
            logging.warning(f"No Go files in {package_path}.")
            return -1

    if result.stdout:
        logging.warning(f"Build error in {package_path}: {result.stdout}")
        return 0
    size = os.path.getsize(f'{package_path}.a')
    os.remove(f'{package_path}.a')
    return size

# recursive process go package and its subdirectories
def process_package(package_path, results, visited, mib=False):
    if package_path in visited:
        return
    visited.add(package_path)
    size = compile_and_get_size(package_path)
    if size == -1:
        for dirname in os.listdir(f"./vendor/{package_path}"):
            dir_full_path = os.path.join(package_path, dirname)
            logging.info(f"Dive into subdirectory {dir_full_path} ...")
            if os.path.isdir(f"./vendor/{dir_full_path}"):
                process_package(dir_full_path, results, visited, mib)
    elif size != 0:
        if mib:
            size = round(size / (1024 * 1024), 1)
        results.append((package_path.replace("./vendor/", ""), size))

# summarize the results by the first N parts of the package path
def summarize_results(results, sum):
    summarized_results = {}
    for dep, size in results:
        parts = dep.split('/')
        if len(parts) >= sum:
            dep = '/'.join(parts[:sum])
        if dep in summarized_results:
            # avoid precision problems caused by floating-point number addition
            summarized_results[dep] = round( summarized_results[dep] + size, 1)
        else:
            summarized_results[dep] = size
    return list(summarized_results.items())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mib", help="display size in MiB", action="store_true")
    parser.add_argument("-sort", help="sort results by size in descending order", action="store_true")
    parser.add_argument("-csv", help="write results to a CSV file", action="store_true")
    parser.add_argument("-d", "--debug", help="enable debug information", action="store_true")
    parser.add_argument("-top", type=int, help='Only print/write the top N lines')
    parser.add_argument("-o", "--out", type=str , default="vendor_packages_size.csv", help='Output csv file name')
    parser.add_argument('-sum', type=int, help='Summarize the sizes by the first N parts of the package path')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    dependencies = get_dependencies()
    logging.debug(f"Dependencies: {dependencies}")

    results = []
    visited = set()
    for dep in dependencies:
        logging.debug(f'Processing {dep}:')
        process_package(dep, results, visited, args.mib)

    if args.sum:
        results = summarize_results(results, args.sum)

    if args.sort or args.top:
        results.sort(key=lambda x: x[1], reverse=True)

    if args.top is not None:
        results = results[:args.top]

    if args.csv:
        with open(args.out, 'w', newline='') as file:
            writer = csv.writer(file)
            if args.mib:
                writer.writerow(["Package", "Size (MiB)"])
            else:
                writer.writerow(["Package", "Size (bytes)"])
            for dep, size in results:
                writer.writerow([dep, size])
    else:
        print("Result: {results}")

if __name__ == "__main__":
    main()
