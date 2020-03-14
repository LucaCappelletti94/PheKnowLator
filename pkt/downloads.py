#!/usr/bin/env python
# -*- coding: utf-8 -*-


# import needed libraries
import datetime
import glob
import os.path
import re
import shutil

from abc import ABCMeta, abstractmethod
from owlready2 import subprocess  # type: ignore
from tqdm import tqdm  # type: ignore
from typing import Dict, List, Optional, TextIO, Tuple

from pkt.utils import gets_ontology_statistics, data_downloader


class DataSource(object):
    """The class takes an input string that contains the file path/name of a text file listing different data sources.
    Each source is shown as a URL.

    The class initiates the downloading of different data sources and generates a metadata file that contains
    important information on each of the files that is downloaded.

    The class has two subclasses which inherit its methods. Each subclass contains an altered version of the primary
    classes methods that are specialized for that specific data type.

    Attributes:
        data_path: A string file path/name to a text file storing URLs of different sources to download.
        data_type: A string specifying the type of data source, which is derived from the data_path attribute (e.g.
            the data_path of 'resources/ontology_source_list.txt' would produce 'ontology_source_list'.
        resource_info: A list of pipe-delimited arguments for how each data source should be processed. For example:
            ['chemical-complex|;;|class-instance|RO_0002436|n|t|0;1|None|None|None`]
        resource_dict: An edge data dictionary where the keys are the edge type and the values are a list containing
            mapping and filtering information (only used for "Edge Data"). For example:
            {node1-node2: node1 - './filepath/mapping_data.txt,
                          col_idx:8 - col_val<2.0 | col_idx:24 - col_val.startswith('REACT'),
                          col_idx:2 - col_val=='reviewed', col_idx:4 - col_val in [9606, 1026]
            }
        source_list: A dictionary, where the key is the type of data and the value is the file path or url. See
            example below: {'chemical-gomf', 'http://ctdbase.org/reports/CTD_chem_go_enriched.tsv.gz',
                            'phenotype': 'http://purl.obolibrary.org/obo/hp.owl'
                            }
        data_files: A dictionary mapping each source identifier to the local location where it was downloaded. For
            example: {'chemical-gomf', 'resources/edge_data/chemical-gomf_CTD_chem_go_enriched.tsv',
                      'phenotype': 'resources/ontologies/hp_with_imports.owl'
                      }
        metadata: A list that stores metadata information for each downloaded data source.

    Raises:
        OSError: If the file pointed to by data_path does not exist.
        TypeError: If the file pointed to by data_path is empty.
        ValueError: If resource_info.txt cannot be found in working directory.
        OSError: If resource_info.txt file does not exist.
        TypeError: If resource_info.txt is an empty file.
    """

    __metaclass__ = ABCMeta

    def __init__(self, data_path: str) -> None:

        # read in data source file
        if not os.path.exists(data_path):
            raise OSError('The {} file does not exist!'.format(data_path))
        elif os.stat(data_path).st_size == 0:
            raise TypeError('Input file: {} is empty'.format(data_path))
        else:
            self.data_path: str = data_path
            self.data_type: str = data_path.split('/')[-1].split('.')[0]

        # read in resource data
        resource_data = glob.glob('**/*resource**info*.txt', recursive=True)

        if len(resource_data) == 0:
            raise ValueError('Could not find resource_info.txt in directory. Please provide this file.')
        elif not os.path.exists(resource_data[0]):
            raise IOError('The {} file does not exist!'.format(resource_data[0]))
        elif os.stat(resource_data[0]).st_size == 0:
            raise TypeError('Input file: {} is empty'.format(resource_data[0]))
        else:
            resource_data_file: TextIO = open(resource_data[0])
            self.resource_info: List = resource_data_file.readlines()
            resource_data_file.close()

        self.resource_dict: Dict[str, List[str]] = {}
        self.source_list: Dict[str, str] = {}
        self.data_files: Dict[str, str] = {}
        self.metadata: List[List[str]] = []

    def parses_resource_file(self) -> None:
        """Verifies that an input file contains data and then outputs a dictionary where each item is a line from the
        input file.

        Returns:
            source_list: A dictionary, where the key is the type of data and the value is the file path or url. See
                example below:
                {'chemical-gomf', 'http://ctdbase.org/reports/CTD_chem_go_enriched.tsv.gz',
                 'phenotype': 'http://purl.obolibrary.org/obo/hp.owl'
                 }

        Raises:
            TypeError: If the file does not contain data.
            ValueError: If there some of the input URLs were improperly formatted.
        """

        pass

    def downloads_data_from_url(self, download_type: str) -> None:
        """Downloads each data source from a list and writes the downloaded file to a directory.

        Args:
            download_type: A string that indicates whether or not the ontologies should be downloaded
                with imported ontologies ('imports').

        Returns:
            data_files: A dictionary mapping each source identifier to the local location where it was downloaded.
                For example: {'chemical-gomf', 'resources/edge_data/chemical-gomf_CTD_chem_go_enriched.tsv',
                              'phenotype': 'resources/ontologies/hp_with_imports.owl'
                              }

        Raises:
            ValueError: If not all of the URLs returned valid data.
        """

        pass

    @staticmethod
    def extracts_edge_metadata(edge) -> Tuple[str, str, str]:
        """Processes edge data metadata and returns a dictionary where the keys are the edge type and the values are
        a list containing mapping and filtering information.

        Args:
            edge: A pipe-delimited string containing information about the edge. For example,

        Returns:
            mapping: Identifier mapping information stored as a node and a filepath to perform identifier mapping on
                (e.g. node1 - './filepath/mapping_data.txt).
            filtering: Filtering criteria including the edge data column index and criteria by which to filter (e.g.
                col_idx:8 - col_val<2.0 | col_idx:24 - col_val.startswith('REACT')).
            evidence criteria: Filtering criteria including the edge data column index and criteria by which to filter
                (e.g. col_idx:2 - col_val=='reviewed', col_idx:4 - col_val in [9606, 1026]).
        """

        # get identifier mapping information
        mapping = ['{} ({})'.format(edge.split('|')[0].split('-')[int(x.split(':')[0])], ''.join(x.split(':')[1]))
                   if x != 'None'
                   else 'None'
                   for x in edge.split('|')[-3].strip('\n').split(';')]

        # get filtering information
        filtering = ['None' if x == 'None'
                     else 'data[{}] {}'.format(x.split(';')[0], ' '.join(x.split(';')[1:]))
                     if ('in' in x.split(';')[1] and x != 'None')
                     else 'data[{}]{}'.format(x.split(';')[0], ''.join(x.split(';')[1:]))
                     for x in edge.split('|')[-1].strip('\n').split('::')]

        # get evidence criteria
        evidence = ['None' if x == 'None'
                    else 'data[{}] {}'.format(x.split(';')[0], ' '.join(x.split(';')[1:]))
                    if ('in' in x.split(';')[1] and x != 'None')
                    else 'data[{}]{}'.format(x.split(';')[0], ''.join(x.split(';')[1:]))
                    for x in edge.split('|')[-2].strip('\n').split('::')]

        return ' | '.join(mapping), ' | '.join(filtering), ' | '.join(evidence)

    def _writes_source_metadata_locally(self) -> None:
        """Writes metadata for each imported data source to a text file.

        Returns:
            None
        """

        # open file to write to and specify output location
        write_loc_part1 = str('/'.join(list(self.data_files.values())[0].split('/')[:-1]) + '/')
        write_loc_part2 = str('_'.join(self.data_type.split('_')[:-1]))

        outfile = open(write_loc_part1 + write_loc_part2 + '_metadata.txt', 'w')
        outfile.write('=' * 35 + '\n{}'.format(self.metadata[0][0]) + '=' * 35 + '\n\n')

        for i in tqdm(range(1, len(self.data_files.keys()) + 1)):
            outfile.write(str(self.metadata[i][0]) + '\n')
            outfile.write(str(self.metadata[i][1]) + '\n')
            outfile.write(str(self.metadata[i][2]) + '\n')
            outfile.write(str(self.metadata[i][3]) + '\n')
            outfile.write(str(self.metadata[i][4]) + '\n')
            outfile.write(str(self.metadata[i][5]) + '\n')
            outfile.write(str(self.metadata[i][6]) + '\n')
            outfile.write(str(self.metadata[i][7]) + '\n')
            outfile.write('\n')

        outfile.close()

        return None

    def generates_source_metadata(self) -> None:
        """Extracts and stores metadata for imported data sources and save the information to the metadata attribute.
        Metadata includes the following information:
            1 - Edge: the name of the edge-type (e.g. 'chemical-gene')
            2 - Data Processing Information: how the data will be processed including: urls/file paths to other data
                sources that will be used to map identifiers or filter the data.
            3 - Data Information: information on the data including: downloaded url, download date, file size in
                bytes, and the local file location it was downloaded to

        Example:
                EDGE: chemical-gobp
                DATA PROCESSING INFO
                    - IDENTIFIER MAPPING = chemical (./resources/processed_data/MESH_CHEBI_MAP.txt)
                    - FILTERING CRITERIA = data[3]==Biological Process
                    - EVIDENCE CRITERIA = data[8]<0.0001
                DATA INFO
                    - DOWNLOAD_URL = http://ctdbase.org/reports/CTD_chem_go_enriched.tsv.gz
                    - DOWNLOAD_DATE = 01/14/2020
                    - FILE_SIZE_IN_BYTES = 760612373
                    - DOWNLOADED_FILE_LOCATION = ./resources/edge_data/chemical-gobp_CTD_chem_go_enriched.tsv

        Returns:
            None.
        """

        print('\n*** Generating Metadata ***\n')
        self.metadata.append(['#' + str(datetime.datetime.utcnow().strftime('%a %b %d %X UTC %Y')) + ' \n'])

        for i in tqdm(self.data_files.keys()):
            source = self.data_files[i]

            # get edge information
            if '-' in source:
                resource_info = self.extracts_edge_metadata([x for x in self.resource_info if x.startswith(i)][0])
                map_info = resource_info[0]
                filter_info = resource_info[1]
                evidence_info = resource_info[2]
            else:
                map_info, filter_info, evidence_info = 'None', 'None', 'None'

            # add metadata for each source as nested list
            source_metadata = ['EDGE: {}'.format(i),
                               'DATA PROCESSING INFO\n  - IDENTIFIER MAPPING = {}'.format(map_info),
                               '  - FILTERING CRITERIA = {}'.format(filter_info),
                               '  - EVIDENCE CRITERIA = {}'.format(evidence_info),
                               'DATA INFO\n  - DOWNLOAD_URL = {}'.format(str(self.source_list[i])),
                               '  - DOWNLOAD_DATE = {}'.format(str(datetime.datetime.now().strftime('%m/%d/%Y'))),
                               '  - FILE_SIZE_IN_BYTES = {}'.format(str(os.stat(self.data_files[i]).st_size)),
                               '  - DOWNLOADED_FILE_LOCATION = {}'.format(str(source))]

            self.metadata.append(source_metadata)

        # write metadata
        self._writes_source_metadata_locally()

        return None

    @abstractmethod
    def gets_data_type(self) -> str:
        """"A string representing the type of data being processed."""

        pass


class OntData(DataSource):

    def gets_data_type(self) -> str:
        """"A string representing the type of data being processed."""

        return 'Ontology Data'

    def parses_resource_file(self) -> None:
        """Parses data from a file and outputs a list where each item is a line from the input text file.

        Returns:
            source_list: A dictionary, where the key is the type of data and the value is the file path or url. See
                example below: {'chemical-gomf', 'http://ctdbase.org/reports/CTD_chem_go_enriched.tsv.gz',
                                'phenotype': 'http://purl.obolibrary.org/obo/hp.owl'
                                }

        Raises:
            TypeError: If the file does not contain data.
            ValueError: If there some of the input URLs were improperly formatted.
        """

        # CHECK - file has data
        if os.stat(self.data_path).st_size == 0:
            raise TypeError('ERROR: input file: {} is empty'.format(self.data_path))
        else:
            data_path_file = open(self.data_path)
            source_list = {row.strip().split(',')[0]: row.strip().split(',')[1].strip()
                           for row in data_path_file.read().split('\n')}
            data_path_file.close()

            # CHECK - verify formatting of urls
            valid_sources = [url for url in source_list.values() if 'purl.obolibrary.org/obo' in url or 'owl' in url]

            if len(source_list) == len(valid_sources):
                self.source_list = source_list
            else:
                raise ValueError('ERROR: Not all URLs were formatted properly')

        return None

    def downloads_data_from_url(self, download_type: Optional[str] = None) -> None:
        """Takes a string representing a file path/name to a text file as an argument. The function assumes
        that each item in the input file list is an URL to an OWL/OBO ontology.

        For each URL, the referenced ontology is downloaded, and used as input to an OWLTools command line argument (
        https://github.com/owlcollab/owltools/wiki/Extract-Properties-Command), which facilitates the downloading of
        ontologies that are imported by the primary ontology. The function will save the downloaded ontology + imported
        ontologies.

        Args:
            download_type: A string that is used to indicate whether or not the ontologies should be downloaded
                with imported ontologies ('imports').

        Returns:
            data_files: A dictionary mapping each source identifier to the local location where it was downloaded.
                For example: {'chemical-gomf', 'resources/edge_data/chemical-gomf_CTD_chem_go_enriched.tsv',
                              'phenotype': 'resources/ontologies/hp_with_imports.owl'
                              }

        Raises:
           ValueError: If not all of the URLs returned valid data.
        """

        # check data before download
        self.parses_resource_file()

        # set location where to write data
        file_loc = './' + '/'.join(self.data_path.split('/')[:-1]) + '/ontologies/'
        print('\n ***Downloading Data: {0} to "{1}" ***\n'.format(self.data_type, file_loc))

        # process data
        for i in tqdm(self.source_list.keys()):
            source = self.source_list[i]
            file_prefix = source.split('/')[-1].split('.')[0]
            write_loc = file_loc + file_prefix

            print('\nDownloading: {}'.format(str(file_prefix)))

            # don't re-download ontologies
            if any(x for x in os.listdir(write_loc.strip(file_prefix)) if re.sub('_with.*.owl', '', x) == file_prefix):
                self.data_files[i] = glob.glob(write_loc.strip(file_prefix) + '*' + file_prefix + '*')[0]
            else:
                if download_type == 'imports' and 'purl' in source:
                    try:
                        subprocess.check_call(['./pkt/libs/owltools',
                                               str(source),
                                               '--merge-import-closure',
                                               '-o',
                                               str(write_loc) + '_with_imports.owl'])

                        self.data_files[i] = str(write_loc) + '_with_imports.owl'
                    except subprocess.CalledProcessError as error:
                        print(error.output)
                elif download_type != 'imports' and 'purl' in source:
                    try:
                        subprocess.check_call(['./pkt/libs/owltools',
                                               str(source),
                                               '-o',
                                               str(write_loc) + '_without_imports.owl'])

                        self.data_files[i] = str(write_loc) + '_without_imports.owl'
                    except subprocess.CalledProcessError as error:
                        print(error.output)
                else:
                    data_downloader(source, file_loc, str(file_prefix) + '_with_imports.owl')
                    self.data_files[i] = file_loc + str(file_prefix) + '_with_imports.owl'

            # print stats
            gets_ontology_statistics(file_loc + str(file_prefix) + '_with_imports.owl')

        # CHECK - make sure all files were processed
        if len(self.source_list) != len(self.data_files):
            raise ValueError('ERROR: Not all URLs returned a data file')

        return None


class LinkedData(DataSource):

    def gets_data_type(self) -> str:
        """"A string representing the type of data being processed."""

        return 'Edge Data'

    def parses_resource_file(self) -> None:
        """Verifies a file contains data and then outputs a list where each item is a line from the input text file.

        Returns:
            source_list: A dictionary, where the key is the type of data and the value is the file path or url. See
                example below: {'chemical-gomf', 'http://ctdbase.org/reports/CTD_chem_go_enriched.tsv.gz',
                                'phenotype': 'http://purl.obolibrary.org/obo/hp.owl'
                                }

        Raises:
            TypeError: If the file does not contain data.
        """

        if os.stat(self.data_path).st_size == 0:
            raise TypeError('ERROR: input file: {} is empty'.format(self.data_path))
        else:
            self.source_list = {row.strip().split(',')[0]: row.strip().split(',')[1].strip()
                                for row in open(self.data_path).read().split('\n')}

        return None

    def downloads_data_from_url(self, download_type: Optional[str] = None) -> None:
        """Takes a string representing a file path/name to a text file as an argument. The function assumes that
        each item in the input file list is a valid URL.

        Args:
            download_type: A string that is used to indicate whether or not the ontologies should be downloaded
                with imported ontologies ('imports'). Within this subclass, this argument is currently ignored.

        Returns:
            data_files: A dictionary mapping each source identifier to the local location where it was downloaded.
                For example: {'chemical-gomf', 'resources/edge_data/chemical-gomf_CTD_chem_go_enriched.tsv',
                              'phenotype': 'resources/ontologies/hp_with_imports.owl'
                              }

        Raises:
            ValueError: If not all of the URLs returned valid data.
        """

        if not download_type:
            self.parses_resource_file()

            # set location where to write data
            file_loc = './' + '/'.join(self.data_path.split('/')[:-1]) + '/edge_data/'
            print('\n*** Downloading Data: {0} to "{1}" ***\n'.format(self.data_type, file_loc))

            for i in tqdm(self.source_list.keys()):
                source = self.source_list[i]
                file_name = re.sub('.gz|.zip|\?.*', '', source.split('/')[-1])
                write_path = file_loc
                print('\nEdge: {edge}'.format(edge=i))

                # if file has already been downloaded, rename it
                if any(x for x in os.listdir(write_path) if '_'.join(x.split('_')[1:]) == file_name):
                    self.data_files[i] = write_path + i + '_' + file_name

                    try:
                        shutil.copy(glob.glob(write_path + '*' + file_name)[0], write_path + i + '_' + file_name)
                    except shutil.SameFileError:
                        pass
                else:
                    self.data_files[i] = write_path + i + '_' + file_name
                    data_downloader(source, write_path, i + '_' + file_name)

            # CHECK
            if len(self.source_list) != len(self.data_files):
                raise ValueError('ERROR: Not all URLs returned a data file')

            return None
