from __future__ import unicode_literals, division, absolute_import
from tests import FlexGetBase
from path import Path


class TestFilesystem(FlexGetBase):
    base = "filesystem_test_dir/"
    test1 = base + '/Test1'
    test2 = base + '/Test2'

    __yaml__ = """
        tasks:
          string:
            filesystem: """ + test1 + """

          list:
           filesystem:
             - """ + test1 + """
             - """ + test2 + """

          object_string:
            filesystem:
              path: """ + test1 + """

          object_list:
            filesystem:
              path:
                - """ + test1 + """
                - """ + test2 + """

          file_mask:
            filesystem:
              path: """ + test1 + """
              mask: '*.mkv'

          regexp_test:
            filesystem:
              path: """ + test1 + """
              regexp: '.*\.(mkv)$'

          recursive_true:
            filesystem:
              path: """ + test1 + """
              recursive: yes

          recursive_2_levels:
            filesystem:
              path: """ + test1 + """
              recursive: 2

          retrieve_files:
            filesystem:
              path: """ + test1 + """
              retrieve: files

          retrieve_files_and_dirs:
            filesystem:
              path: """ + test1 + """
              retrieve:
                - files
                - dirs

          combine_1:
            filesystem:
              path: """ + test1 + """
              mask: '*.mkv'
              recursive: 2

          combine_2:
            filesystem:
              path: """ + test1 + """
              recursive: yes
              retrieve: dirs
        """

    item_list = ['file1.mkv', 'file2.txt', 'file10.mkv', 'file11.txt', 'file4.avi', 'file3.xlsx', 'file5.mkv', 'dir1',
                 'dir2', 'dir4', 'dir6', 'dir7', 'dir8']

    def assert_check(self, task_name, test_type, filenames):
        for file in filenames:
            file = Path(file)
            if test_type == 'positive':
                assertion_error = 'Failed %s %s test, did not find %s' % (test_type, task_name, file)
                assert self.task.find_entry(title=file.namebase), assertion_error
            else:
                assertion_error = 'Failed %s %s test, found %s' % (test_type, task_name, file)
                assert not self.task.find_entry(title=file.namebase), assertion_error

    def test_string(self):
        task_name = 'string'
        should_exist = 'dir1', 'dir2', 'file1.mkv', 'file2.txt'
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_list(self):
        task_name = 'list'
        should_exist = ['dir1', 'dir2', 'file1.mkv', 'file2.txt', 'file10.mkv']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_object_string(self):
        task_name = 'object_string'
        should_exist = ['dir1', 'dir2', 'file1.mkv', 'file2.txt']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_object_list(self):
        task_name = 'object_list'
        should_exist = ['dir1', 'dir2', 'file1.mkv', 'file2.txt', 'file10.mkv']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_file_mask(self):
        task_name = 'file_mask'
        should_exist = ['file1.mkv']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_regexp_test(self):
        task_name = 'regexp_test'
        should_exist = ['file1.mkv']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_recursive_true(self):
        task_name = 'recursive_true'
        should_exist = ['dir1', 'dir4', 'dir6', 'dir7', 'dir8', 'file11.txt', 'file4.avi', 'file3.xlsx', 'dir2',
                        'file5.mkv', 'file1.mkv', 'file2.txt']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_recursive_2_levels(self):
        task_name = 'recursive_2_levels'
        should_exist = ['dir1', 'dir4', 'file3.xlsx', 'dir2', 'file5.mkv', 'file1.mkv', 'file2.txt']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_retrieve_files(self):
        task_name = 'retrieve_files'
        should_exist = ['file1.mkv', 'file2.txt']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_retrieve_files_and_dirs(self):
        task_name = 'retrieve_files_and_dirs'
        should_exist = ['dir1', 'dir2', 'file1.mkv', 'file2.txt']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_combine_1(self):
        task_name = 'combine_1'
        should_exist = ['file5.mkv', 'file1.mkv']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)

    def test_combine_2(self):
        task_name = 'combine_2'
        should_exist = ['dir1', 'dir4', 'dir2', 'dir6', 'dir7', 'dir8']
        should_not_exist = [item for item in self.item_list if item not in should_exist]
        self.execute_task(task_name)

        self.assert_check(task_name, 'positive', should_exist)
        self.assert_check(task_name, 'negative', should_not_exist)