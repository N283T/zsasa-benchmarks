{
  description = "Reproducible benchmark harness for zsasa manuscript evidence";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    zig-overlay = {
      url = "github:mitchellh/zig-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    zsasa = {
      url = "github:N283T/zsasa/v0.6.0";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.zig-overlay.follows = "zig-overlay";
    };
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      zig-overlay,
      zsasa,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        zig = zig-overlay.packages.${system}."0.16.0";
        zsasaZigDeps = pkgs.runCommand "zsasa-zig-deps"
          {
            src = zsasa;
            nativeBuildInputs = [ zig ];
            outputHashAlgo = "sha256";
            outputHashMode = "recursive";
            outputHash = "sha256-30G6nwi2dPa3iqZT/xr4se2bRhigiaSC90JDswDjNmU=";
          }
          ''
            export ZIG_GLOBAL_CACHE_DIR=$(mktemp -d)
            cp -r $src/. .
            zig build --fetch
            mv $ZIG_GLOBAL_CACHE_DIR/p $out
          '';
        zsasaCli = pkgs.stdenv.mkDerivation {
          pname = "zsasa";
          version = "0.6.0";
          src = zsasa;
          nativeBuildInputs = [ zig ];
          dontConfigure = true;
          dontFixup = true;
          buildPhase = ''
            export ZIG_GLOBAL_CACHE_DIR=$(mktemp -d)
            mkdir -p "$ZIG_GLOBAL_CACHE_DIR"
            cp -R ${zsasaZigDeps} "$ZIG_GLOBAL_CACHE_DIR/p"
            chmod -R u+w "$ZIG_GLOBAL_CACHE_DIR/p"
            zig build \
              -Doptimize=ReleaseFast \
              --global-cache-dir "$ZIG_GLOBAL_CACHE_DIR" \
              --prefix $out \
              -j$NIX_BUILD_CORES
          '';
          installPhase = ''
            true
          '';
          meta = with pkgs.lib; {
            description = "Pinned zsasa CLI for benchmark reruns";
            homepage = "https://github.com/N283T/zsasa";
            license = licenses.mit;
            mainProgram = "zsasa";
            platforms = platforms.unix;
          };
        };
        python = pkgs.python312.withPackages (ps: [
          ps.rich
          ps.typer
        ]);
      in
      {
        packages.zsasa = zsasaCli;

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            zig
            zsasaCli
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
            export ZSASA_CLI="${zsasaCli}/bin/zsasa"
            echo "zsasa benchmark shell"
            echo "- zsasa CLI: $ZSASA_CLI"
            echo "- Run: python scripts/check_scaffold.py"
            echo "- Dry run validation refresh: uv run python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --dry-run"
          '';
        };
      }
    );
}
