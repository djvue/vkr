import datasets
from dataset.prompt import get_package_rows
from tqdm import tqdm


test_candidates_ds = datasets.load_from_disk('./data/test_candidates_ds').filter(lambda row: row['project_path'] == 'b91cfd8484e26a5190998f274bf1f56f1d61804a/' and row['relative_go_package'] == 'pkg/cmd/variable/set/')

package_candidates = set()

for row in test_candidates_ds:
    package_candidates.add((row['project_path'], row['relative_go_package']))

def package_candidates_ds_row_generator():
    for (project_path, relative_go_package) in package_candidates:
        yield {"project_path": project_path, 'relative_go_package': relative_go_package}

package_candidates_ds = datasets.Dataset.from_generator(package_candidates_ds_row_generator)

print(package_candidates_ds)

print(package_candidates_ds[0])

# def transform_to_funcs(rows):
#     columns = ['project_path', 'relative_go_package', 'func_name', 'input_code', 'prompt']
#     res = {column: [] for column in columns}

#     for project_path, relative_go_package in zip(rows['project_path'], rows['relative_go_package']):
#         items = get_package_rows(project_path, relative_go_package)

#         for item in items:
#             for column in columns:
#                 res[column].append(item[column])

#     return res

# final_ds = package_candidates_ds.take(100).map(transform_to_funcs, batched=True, batch_size=1, num_proc=1)
error_count = 0
#for row in tqdm(package_candidates_ds):
for row in package_candidates_ds.take(1):
    try:
        items = get_package_rows(row['project_path'], row['relative_go_package'])
        for item in items:
            if item['func_name'] != 'setVariable':
                continue
            print(item['func_name'])
            print(item['input_code'])
    except Exception as e:
        error_count += 1
        print(e)

print('error count', error_count)


#final_ds.save_to_disk('./data/final_ds')

#print(final_ds)
#print(final_ds[0])
