import functools

from commoncode.resource import Codebase


class ScancodeCodebase(Codebase):
    def __init__(self, *args, with_info=True, **kwargs, ):
        self.with_info = with_info
        super().__init__(*args, **kwargs, )

    def save_initial_counts(self):
        files_count, dirs_count, size_count = self.compute_counts()
        self.save_counts('initial', dirs_count, files_count, size_count)

    def save_final_counts(self, strip_root):
        files_count, dirs_count, size_count = self.compute_counts(skip_root=strip_root, skip_filtered=True)
        self.save_counts('final', dirs_count, files_count, size_count)

    def save_counts(self, phase, dirs_count, files_count, size_count):
        self.counters[('%s:files_count' % phase)] = files_count
        self.counters[('%s:dirs_count' % phase)] = dirs_count
        self.counters[('%s:size_count' % phase)] = size_count

    @functools.cache
    def _load_resource(self, path):
        return super()._load_resource(path)