from dcmrtstruct2nii.tests.utils.dataset_bmia import list_subjects_stwstrategyhn1, download_subject
from dcmrtstruct2nii.tests.utils import compare_mask 
from pathlib import Path
from dcmrtstruct2nii import dcmrtstruct2nii
import shutil
import json
import warnings


def gen_compare_list(tmpdir, keep_files=False):
    dataset = Path(tmpdir) / 'stwstrategyhn1'
    dcmrtstruct2niidir = Path(tmpdir) / 'dcmrtstruct2nii'

    dcmrtstruct2niidir.mkdir(exist_ok=True)

    counter = 0
    subjects = list_subjects_stwstrategyhn1()
    numsubjects = len(subjects)

    result = {}

    for subject in subjects:
        counter += 1
        print(f'Comparing {subject.label} {counter}/{numsubjects}')

        subject_dir = Path(dataset / subject.label)
        download_subject(subject, subject_dir)

        rtstructs = list(subject_dir.glob('*/scans/*/resources/secondary/files/*'))
        if len(rtstructs) > 1 or len(rtstructs) <= 0:
            assert False, f'> 1 RTSTRUCT or <= 0 RTSTRUCT found for subject {subject.label}, something changed in the dataset?'
        rtstruct = rtstructs[0]

        dicoms = list(subject_dir.glob('*/scans/*/resources/DICOM/files'))
        if len(dicoms) > 1 or len(dicoms) <= 0:
            assert False, f'> 1 DICOM or <= 0 DICOM found for subject {subject.label}, something changed in the dataset?'

        dicom = dicoms[0]

        subjoutdir = Path(dcmrtstruct2niidir / subject.label)
        subjoutdir.mkdir(exist_ok=True)

        dcmrtstruct2nii(rtstruct, dicom, subjoutdir)

        niicounter = 0
        for nii in subjoutdir.glob('*.nii.gz'):
            if nii.name == 'image.nii.gz':
                # skip main image
                continue 

            niicounter += 1
            niftis = list(subject_dir.glob(f'**/{nii.name}'))

            if len(niftis) > 1 or len(niftis) <= 0:
                assert False, f'> 1 niftis or <= 0 niftis {nii.name} found for subject {subject.label}, something changed in the dataset?'

            nii_stwstrategyhn1 = niftis[0]

            diff = compare_mask(nii, nii_stwstrategyhn1)
           
            k = str(nii.relative_to(dcmrtstruct2niidir))
            result[k] = diff


        print(f"Compared {niicounter} NiFTI's for subject {subject.label}")


        if not keep_files:
            # cleanup, GitHub runners only have ~14 GB of space
            shutil.rmtree(subjoutdir)
            shutil.rmtree(subject_dir)

    return result


def _cmp_left_right(left, right, key, cmpfunc):
    union = set(left.keys()).union(right.keys())

    results = {} 
    for k in union:
        if k not in left:
            warnings.warn(f'compare left right: {k} not in left')
            continue

        if k not in right:
            warnings.warn(f'compare left right: {k} not in right')
            continue

        if not cmpfunc(left[k][key], right[k][key]):
            warnings.warn(f'{left[k][key]} cmp {right[k][key]}')
            results[k] = False
        else:
            results[k] = True

    return results


def test_bmia_stwstrategyhn1(tmpdir):
    with open('lookup.json', 'r') as fh:
        left = json.load(fh)
    
    right = gen_compare_list(tmpdir)
    
    # check if the Intersection over Union is within .1 of the expected value
    assert all(_cmp_left_right(left, right, 'iou', lambda x, y: abs(x - y) < .1).values())

    # compare mask hashes, throw warning if not equal 
    hashes = _cmp_left_right(left, right, 'h_pred', lambda x, y: x == y)

    if not all(hashes.values()):
        for k, v in hashes.items():
            if not v:
                warnings.warn(f'{k} hash not equal: {left[k]["h_pred"]} - {right[k]["h_pred"]}')
        

if __name__ == '__main__':
    print('Generating lookup tables for pytest...')
    datadir = Path('/tmp/dcmrtstruct2nii_test')
    datadir.mkdir()
    data = gen_compare_list(datadir, keep_files=True)
    with open(datadir / 'lookup.json', 'w') as fh:
        json.dump(data, fh)
