{
  description = "Reproducible benchmark harness for zsasa manuscript evidence";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    zig-overlay = {
      url = "github:mitchellh/zig-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      zig-overlay,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        zig = zig-overlay.packages.${system}."0.16.0";
        python = pkgs.python312.withPackages (ps: [
          ps.matplotlib
          ps.numpy
          ps.polars
          ps.pyarrow
          ps.rich
          ps.typer
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            zig
            python
            uv
            hyperfine
            git
            jq
            zstd
            duckdb
            pkg-config
            autoconf
            automake
            libtool
            cmake
            cargo
            rustc
            zlib
          ];

          shellHook = ''
            export ZSASA_BENCH_ROOT="$PWD"
            echo "zsasa benchmark shell"
            echo "- Run: python scripts/check_scaffold.py"
            echo "- Dry run validation refresh: python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --dry-run"
          '';
        };
      }
    );
}
