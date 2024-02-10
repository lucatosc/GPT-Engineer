"""
Module for running benchmarks.

This module defines functions to run benchmarks using a given agent and to print
the results of the benchmark tasks.

Functions
---------
run : function
    Runs the benchmark tasks using the provided agent and returns a list of TaskResult objects.

print_results : function
    Prints the results of the benchmark tasks to the console.
"""
import time

from typing import List, Optional

from gpt_engineer.benchmark.types import Assertable, Benchmark, TaskResult
from gpt_engineer.core.base_agent import BaseAgent
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv


def run(
    agent: BaseAgent,
    benchmark: Benchmark,
    task_name: Optional[str] = None,
    verbose=False,
) -> List[TaskResult]:
    """
    Runs the benchmark tasks using the provided agent and returns a list of TaskResult objects.

    Parameters
    ----------
    agent : BaseAgent
        The agent to use for running the benchmark tasks.
    benchmark : Benchmark
        The benchmark containing the tasks to run.
    task_name : Optional[str], default=None
        An optional name of a specific task to run within the benchmark.
    verbose : bool, default=False
        A flag to indicate whether to print verbose output during the benchmark.

    Returns
    -------
    List[TaskResult]
        A list of TaskResult objects representing the results of the benchmark tasks.
    """
    task_results = []
    for task in benchmark.tasks:
        t0 = time.time()
        files_dict = agent.improve(task.initial_code, task.prompt, task.command)
        t1 = time.time()

        env = DiskExecutionEnv()
        env.upload(files_dict)

        if task.command:
            p = env.popen(task.command)
            stdout, stderr = p.communicate(benchmark.timeout)
            stdout, stderr = stdout.decode("utf-8"), stderr.decode("utf-8")
        else:
            p, stdout, stderr = None, None, None
        exec_result = Assertable(
            files=files_dict,
            env=env,
            process=p,
            stdout=stdout,
            stderr=stderr,
        )

        task_results.append(
            TaskResult(
                task_name=task.name,
                assertion_results={
                    assertion_name: assertion(exec_result)
                    for assertion_name, assertion in task.assertions.items()
                },
                duration=t1 - t0,
            )
        )
        if verbose:
            print_results(task_results)
    return task_results


def print_results(results: list[TaskResult]):
    """
    Prints the results of the benchmark tasks to the console.

    Parameters
    ----------
    results : list[TaskResult]
        A list of TaskResult objects representing the results of the benchmark tasks.

    Returns
    -------
    None
    """
    for task_result in results:
        print(f"\n--- Results for {task_result.task_name} ---")
        print(f"{task_result.task_name} ({task_result.duration:.2f}s)")
        for assertion_name, assertion_result in task_result.assertion_results.items():
            checkmark = "✅" if assertion_result else "❌"
            print(f"  {checkmark} {assertion_name}")
        print()

    total_time = sum(task_result.duration for task_result in results)
    print(f"Total time: {total_time:.2f}s")

    correct_assertions = sum(
        sum(
            assertion_result
            for assertion_result in task_result.assertion_results.values()
        )
        for task_result in results
    )
    total_assertions = sum(
        len(task_result.assertion_results) for task_result in results
    )
    print(f"Total correct assertions: {correct_assertions}/{total_assertions}")

    correct_tasks = sum(
        all(
            assertion_result
            for assertion_result in task_result.assertion_results.values()
        )
        for task_result in results
    )
    print(f"Correct tasks: {correct_tasks}/{len(results)}")
    print()
