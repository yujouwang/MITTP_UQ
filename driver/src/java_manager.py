from pathlib import Path
import logging
logger = logging.getLogger(__name__)

class JavaManager:
    def __init__(self, java_filepath):
        self.java_filepath = Path(java_filepath)
        assert self.java_filepath.exists()

    def prepare_files(self):
        """ Put the customized operation in this function 
        """
        raise NotImplementedError


class JavaUqBepuStageRun(JavaManager):
    def __init__(self, java_filepath, java_keywords):
        self.java_filepath = [Path(p) for p in java_filepath]
        for p in self.java_filepath:
            assert p.exists(), f"Java file {p} does not exist"
        self.java_keywords = java_keywords
    

    def prepare_files(self, bepu_input_dict, dst_folder):
        """ Prepare the Java file for the UQ simulation 
            Two steps:
            1. Replace the keywords specified in `java_keywords` dictionary: for starccm control
                e.g.,  the JAVANAME, STOPTIME, TIMESTEP in the Java file
            2. Replace the BEPU input parameters specified in `bepu_input_dict` dictionary

            Input:
                bepu_input_dict: a dictionary of BEPU input parameters to be replaced in the Java file
                dst_folder: path to the destination folder
        """
        for src in self.java_filepath:
            self._prepare(src, bepu_input_dict, dst_folder)

    def _prepare(self, src, bepu_input_dict, dst_folder):

        with open(src, 'r', encoding='utf-8') as f:
            content = f.read()

        # Step 1, replace the java keywords ()
        for k, v in self.java_keywords.items():
            content = content.replace(k, v)
        
        # Step 2, replace the BEPU input parameters
        for k, v in bepu_input_dict.items():
            content = content.replace(k, str(v))

        # Write
        file_name = Path(src).name
        dst = dst_folder / file_name
        print(dst)
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(content)
        assert dst.exists()
        return 
