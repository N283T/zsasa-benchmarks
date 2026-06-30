#!/usr/bin/env julia

using JSON
using PDBTools
using Statistics

function parse_args(argv)
    values = Dict{String,String}(
        "selection" => "protein",
        "n_dots" => "100",
        "timing_repeats" => "3",
    )
    flags = Set{String}()
    i = 1
    while i <= length(argv)
        arg = argv[i]
        if arg == "--timing"
            push!(flags, "timing")
            i += 1
        elseif arg in ["--input", "--output", "--selection", "--n-dots", "--timing-repeats"]
            i == length(argv) && error("missing value for $arg")
            key = replace(arg[3:end], "-" => "_")
            values[key] = argv[i + 1]
            i += 2
        else
            error("unknown argument: $arg")
        end
    end
    for key in ["input", "output"]
        haskey(values, key) || error("missing required --$(replace(key, "_" => "-"))")
    end
    return values, flags
end

function compute_once(input::String, selection::String, n_dots::Int; parallel::Bool)
    parse_seconds = @elapsed atoms = read_pdb(input, selection)
    sasa_result = nothing
    sasa_seconds = @elapsed sasa_result = sasa_particles(atoms; n_dots=n_dots, parallel=parallel)
    total_area = sasa(sasa_result)
    return atoms, total_area, parse_seconds, sasa_seconds
end

function write_result(output::String, input::String, atoms, total_area, n_dots::Int)
    mkpath(dirname(output))
    open(output, "w") do io
        JSON.print(io, Dict(
            "filename" => input,
            "n_atoms" => length(atoms),
            "n_dots" => n_dots,
            "total_area" => total_area,
            "tool" => "pdbtools_jl",
        ))
        println(io)
    end
end

function main(argv)
    args, flags = parse_args(argv)
    input = args["input"]
    output = args["output"]
    selection = args["selection"]
    n_dots = parse(Int, args["n_dots"])
    timing_repeats = max(1, parse(Int, args["timing_repeats"]))
    parallel = Threads.nthreads() > 1

    if "timing" in flags
        compute_once(input, selection, n_dots; parallel=parallel)
        parse_ms = Float64[]
        sasa_ms = Float64[]
        total_ms = Float64[]
        last_atoms = nothing
        last_total = 0.0
        for _ in 1:timing_repeats
            GC.gc()
            atoms, total_area, parse_seconds, sasa_seconds = compute_once(
                input,
                selection,
                n_dots;
                parallel=parallel,
            )
            last_atoms = atoms
            last_total = total_area
            push!(parse_ms, parse_seconds * 1000)
            push!(sasa_ms, sasa_seconds * 1000)
            push!(total_ms, (parse_seconds + sasa_seconds) * 1000)
        end
        write_result(output, input, last_atoms, last_total, n_dots)
        println(stderr, "PARSE_TIME_MS:", median(parse_ms))
        println(stderr, "SASA_TIME_MS:", median(sasa_ms))
        println(stderr, "TOTAL_TIME_MS:", median(total_ms))
    else
        atoms, total_area, _, _ = compute_once(input, selection, n_dots; parallel=parallel)
        write_result(output, input, atoms, total_area, n_dots)
    end
end

main(ARGS)
