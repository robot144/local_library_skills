# local_library_search reuses the library local_library_add_docs builds,
# rather than building its own - this stages a copy into its run dir so the
# two test cases stay independent runs (no shared mutable state between them).
rule stage_search_library:
    input:
        "scratch/local_library_add_docs/default/subject_result.json",
    output:
        directory("scratch/local_library_search/{size}/run/local_library"),
    params:
        source="scratch/local_library_add_docs/default/run/local_library",
    shell:
        "rm -rf {output} && cp -r {params.source} {output}"
