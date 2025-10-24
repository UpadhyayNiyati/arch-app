class FileTooLargeError(Exception):
    def __init__(self, filename, limit_mb):
        self.filename = filename
        self.limit_mb = limit_mb
        super().__init__(f"File '{filename}' exceeds the {limit_mb} MB limit.")
