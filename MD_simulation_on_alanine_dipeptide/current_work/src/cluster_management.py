from config import *
import copy, pickle, re, os, time, subprocess, datetime, itertools

class cluster_management(object):
    def __init__(self):
        return

    @staticmethod
    def create_sge_files_for_commands(list_of_commands_to_run):
        for item in list_of_commands_to_run:
            sge_filename = '../sge_files/' + item.replace(' ', '_') + '.sge'
            content_for_sge_files = '''#!/bin/bash

#$ -S /bin/bash           # use bash shell
#$ -V                     # inherit the submission environment
#$ -cwd                   # start job in submission directory

#$ -m ae                 # email on abort, begin, and end
#$ -M wei.herbert.chen@gmail.com         # email address

#$ -q all.q               # queue name
#$ -l h_rt=%s       # run time (hh:mm:ss)
####$ -l hostname=compute-0-3

%s

echo "This job is DONE!"

exit 0
''' % (CONFIG_19, command)
            with open(sge_filename, 'w') as f_out:
                f_out.write(content_for_sge_files)
                f_out.write("\n")
        return

    @staticmethod
    def get_num_of_running_jobs():
        output = subprocess.check_output(['qstat'])
        num_of_running_jobs = len(re.findall('weichen9', output))
        print('checking number of running jobs = %d\n' % num_of_running_jobs)
        return num_of_running_jobs

    @staticmethod
    def submit_sge_jobs_and_archive_files(job_file_lists,
                                          num,  # num is the max number of jobs submitted each time
                                          flag_of_whether_to_record_qsub_commands = False
                                          ):
        dir_to_archive_files = '../sge_files/archive/'

        if not os.path.exists(dir_to_archive_files):
            os.makedirs(dir_to_archive_files)

        assert(os.path.exists(dir_to_archive_files))

        for item in job_file_lists[0:num]:
            subprocess.check_output(['qsub', item])
            print('submitting ' + str(item))
            subprocess.check_output(['mv', item, dir_to_archive_files]) # archive files
        return

    @staticmethod
    def get_sge_files_list():
        result = filter(lambda x: x[-3:] == "sge",subprocess.check_output(['ls', '../sge_files']).split('\n'))
        result = map(lambda x: '../sge_files/' + x, result)
        return result

    @staticmethod
    def submit_new_jobs_if_there_are_too_few_jobs(num):
        if cluster_management.get_num_of_running_jobs() < num:
            job_list = cluster_management.get_sge_files_list()
            cluster_management.submit_sge_jobs_and_archive_files(job_list, num)
        return

    @staticmethod
    def monitor_status_and_submit_periodically(num,
                                               num_of_running_jobs_when_allowed_to_stop = 0,
                                               monitor_mode = 'normal',  # monitor_mode determines whether it can go out of first while loop
                                               ):
        if monitor_mode == 'normal':
            min_num_of_unsubmitted_jobs = 0
        elif monitor_mode == 'always_wait_for_submit':
            min_num_of_unsubmitted_jobs = -1

        num_of_unsubmitted_jobs = len(cluster_management.get_sge_files_list())
        # first check if there are unsubmitted jobs
        while num_of_unsubmitted_jobs > min_num_of_unsubmitted_jobs:
            time.sleep(10)
            try:
                cluster_management.submit_new_jobs_if_there_are_too_few_jobs(num)
                num_of_unsubmitted_jobs = len(cluster_management.get_sge_files_list())
            except:
                print("not able to submit jobs!\n")

        # then check if all jobs are done
        while cluster_management.get_num_of_running_jobs() > num_of_running_jobs_when_allowed_to_stop:
            time.sleep(10)
        return

    @staticmethod
    def is_job_running_on_cluster(job_sgefile_name):
        output = subprocess.check_output(['qstat', '-r'])
        return job_sgefile_name in output

    @staticmethod
    def check_whether_job_finishes_successfully(job_sgefile_name, latest_version = True):
        """
        return value:
        0: finishes successfully
        1: finishes with exception
        2: aborted due to time limit or other reason
        -1: job does not exist
        """
        job_finished_message = 'This job is DONE!\n'
        # first we check whether the job finishes
        if cluster_management.is_job_running_on_cluster(job_sgefile_name):
            return 0  # not finished
        else:
            all_files_in_this_dir = subprocess.check_output(['ls']).split()

            out_file_list = filter(lambda x: job_sgefile_name in x and ".o" in x, all_files_in_this_dir)
            err_file_list = filter(lambda x: job_sgefile_name in x and ".e" in x, all_files_in_this_dir)

            if len(out_file_list) == 0 or len(err_file_list) == 0:
                return -1   # job does not exist

            if latest_version:
                job_serial_number_list = map(lambda x: int(x.split('.sge.o')[1]), out_file_list)
                job_serial_number_of_latest_version = max(job_serial_number_list)
                latest_out_file = filter(lambda x: str(job_serial_number_of_latest_version) in x, out_file_list)[0]
                latest_err_file = filter(lambda x: str(job_serial_number_of_latest_version) in x, err_file_list)[0]
                with open(latest_out_file, 'r') as out_f:
                    out_content = out_f.readlines()
                with open(latest_err_file, 'r') as err_f:
                    err_content = err_f.readlines()
                    err_content = filter(lambda x: x[:4] != 'bash', err_content)  # ignore error info starting with "bash"

                if (job_finished_message in out_content) and (len(err_content) != 0):
                    return 1  # ends with exception
                elif not job_finished_message in out_content:
                    return 2  # aborted due to time limit or other reason
            else:
                # TODO: handle this case
                return