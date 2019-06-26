import paramiko
import re


def get_paramiko_client(host, username, key_file):
    key = paramiko.RSAKey.from_private_key_file(key_file)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, pkey=key)
    return client


def submit_job(client: paramiko.SSHClient, workflow_dir, job_file):
    """
    Submits Condor-Job and returns the ID and a (start, end) of the sub-id range as a Dict.
    """
    stdin, stdout, stderr = client.exec_command("cd {wf_dir}; condor_submit {job} -terse".format(wf_dir=workflow_dir,
                                                                                                 job=job_file))

    error = ""
    for err in stderr:
        error += err

    if error != "":
        raise ValueError("An error with condor_submit occurred: {error}".format(error=error))

    for output in stdout:
        if output.find("ERROR") != -1:
            raise Exception(output)
        job_id = output.split(".")[0]
        id_range = tuple(output.split(" - "))

    return {
        "id": job_id,
        "range": id_range
    }


def get_job_status(client: paramiko.SSHClient, job_id):
    """
    Determines, job-status. If all jobs were run (status="done"), total_jobs and everything else will be 0
    """
    stdin, stdout, stderr = client.exec_command("condor_q {job_id}".format(job_id=job_id))

    status = None
    for output in stdout:
        if output.find("jobs;") != -1:
            status = list(map(int, re.findall(r'\d+', output)))

    if status is None or len(status) != 7:
        raise Exception("Couldn't parse condor_q")

    return {
        "status": "done" if status[0] == 0 else "running",
        "total_jobs": status[0],
        "completed": status[1],
        "idle": status[3],
        "running": status[4],
        "held": status[5]
    }