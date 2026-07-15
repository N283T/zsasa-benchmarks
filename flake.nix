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
    zsasa_0_9_0 = {
      url = "github:N283T/zsasa/v0.9.0";
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
      zsasa_0_9_0,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        zig = zig-overlay.packages.${system}."0.16.0";
        mkZsasaCli =
          {
            version,
            src,
            zigDepsHash,
          }:
          let
            zigDeps = pkgs.runCommand "zsasa-${version}-zig-deps"
              {
                inherit src;
                nativeBuildInputs = [ zig ];
                outputHashAlgo = "sha256";
                outputHashMode = "recursive";
                outputHash = zigDepsHash;
              }
              ''
                export ZIG_GLOBAL_CACHE_DIR=$(mktemp -d)
                cp -r $src/. .
                zig build --fetch
                mv $ZIG_GLOBAL_CACHE_DIR/p $out
              '';
          in
          pkgs.stdenv.mkDerivation {
            pname = "zsasa";
            inherit version src;
            nativeBuildInputs = [ zig ];
            dontConfigure = true;
            dontFixup = true;
            buildPhase = ''
              export ZIG_GLOBAL_CACHE_DIR=$(mktemp -d)
              mkdir -p "$ZIG_GLOBAL_CACHE_DIR"
              cp -R ${zigDeps} "$ZIG_GLOBAL_CACHE_DIR/p"
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
        zsasaCli = mkZsasaCli {
          version = "0.6.0";
          src = zsasa;
          zigDepsHash = "sha256-XgIsmn9/8bgfTkJP4+oosvl8nasl7MB4GcEtwYaP+eM=";
        };
        zsasaCli09 = mkZsasaCli {
          version = "0.9.0";
          src = zsasa_0_9_0;
          zigDepsHash = "sha256-XgIsmn9/8bgfTkJP4+oosvl8nasl7MB4GcEtwYaP+eM=";
        };
        zsasaVersioned06 = pkgs.writeShellScriptBin "zsasa-0.6.0" ''
          exec ${zsasaCli}/bin/zsasa "$@"
        '';
        zsasaVersioned09 = pkgs.writeShellScriptBin "zsasa-0.9.0" ''
          exec ${zsasaCli09}/bin/zsasa "$@"
        '';
        freesasaCli = pkgs.stdenv.mkDerivation {
          pname = "freesasa";
          version = "2.1.3-9c9f204";
          src = pkgs.fetchFromGitHub {
            owner = "N283T";
            repo = "freesasa";
            rev = "9c9f204fd990ba2f50f47be8d4b96a61355f7a10";
            hash = "sha256-r0moc09QIyDSm/G2ehiZQ0FKnJQZuSdieVHZXNxO3gI=";
          };
          nativeBuildInputs = with pkgs; [ autoconf automake libtool pkg-config ];
          configurePhase = ''
            runHook preConfigure
            autoreconf -i
            ./configure --prefix=$out --enable-threads --disable-json --disable-xml
            runHook postConfigure
          '';
          enableParallelBuilding = true;
          meta = with pkgs.lib; {
            description = "Pinned FreeSASA fork with timing for benchmark reruns";
            homepage = "https://github.com/N283T/freesasa";
            license = licenses.mit;
            mainProgram = "freesasa";
            platforms = platforms.unix;
          };
        };
        freesasaBatch = pkgs.stdenv.mkDerivation {
          pname = "freesasa_batch";
          version = "0.1.0";
          src = ./tools/freesasa_batch;
          nativeBuildInputs = [ pkgs.pkg-config ];
          buildPhase = ''
            runHook preBuild
            c++ -O3 -std=c++17 -I ${freesasaCli}/include \
              -o freesasa_batch freesasa_batch.cc \
              ${freesasaCli}/lib/libfreesasa.a -lpthread
            runHook postBuild
          '';
          installPhase = ''
            runHook preInstall
            install -Dm755 freesasa_batch $out/bin/freesasa_batch
            runHook postInstall
          '';
          meta = with pkgs.lib; {
            description = "Batch wrapper around the FreeSASA C API for benchmark reruns";
            license = licenses.mit;
            mainProgram = "freesasa_batch";
            platforms = platforms.unix;
          };
        };
        rustsasaCli = pkgs.rustPlatform.buildRustPackage {
          pname = "rust-sasa";
          version = "0.9.2-c3c9c4d-timing";
          src = pkgs.fetchFromGitHub {
            owner = "maxall41";
            repo = "RustSASA";
            rev = "c3c9c4da021c2d0a8822ca5b8c8b14fede1e6da1";
            fetchSubmodules = true;
            hash = "sha256-d+gn2peN7Xqj8nlwcQnwtYkcjkRiR0CgPi/+NCKHK0E=";
          };
          patches = [ ./nix/patches/rustsasa-add-timing.patch ];
          cargoHash = "sha256-Rt3+hQYCX6/kJIpEPMcICRvdtDMLFlg2lYBTLB7yzxA=";
          buildFeatures = [ "cli" ];
          doCheck = false;
          meta = with pkgs.lib; {
            description = "Pinned RustSASA CLI synced to upstream with benchmark timing support";
            homepage = "https://github.com/maxall41/RustSASA";
            license = licenses.mit;
            mainProgram = "rust-sasa";
            platforms = platforms.unix;
          };
        };
        lahutaCli = pkgs.stdenv.mkDerivation {
          pname = "lahuta";
          version = "2.0.3";
          src = pkgs.fetchFromGitHub {
            owner = "bisejdiu";
            repo = "lahuta";
            rev = "136411ee6ac797cab84a35d8183e6be6e6a270b2";
            fetchSubmodules = true;
            hash = "sha256-VzHfYATMDkhRrJOXH7rq/am5+QZluyQFsXu6vGM5Ky4=";
          };
          nativeBuildInputs = with pkgs; [ cmake pkg-config ];
          cmakeFlags = [
            "-DCMAKE_BUILD_TYPE=Release"
            "-DLAHUTA_BUILD_CLI=ON"
            "-DLAHUTA_BUILD_PYTHON=OFF"
            "-DLAHUTA_BUILD_SHARED_CORE=OFF"
            "-DLAHUTA_BUILD_EXAMPLES=OFF"
            "-DLAHUTA_ENABLE_LTO=OFF"
            "-DLAHUTA_NATIVE_ARCH=OFF"
            "-DBUILD_TESTING=OFF"
          ];
          enableParallelBuilding = true;
          meta = with pkgs.lib; {
            description = "Pinned Lahuta CLI for benchmark reruns";
            homepage = "https://github.com/bisejdiu/lahuta";
            license = licenses.mit;
            mainProgram = "lahuta";
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
        packages.zsasa_0_6_0 = zsasaVersioned06;
        packages.zsasa_0_9_0 = zsasaVersioned09;
        packages.freesasa = freesasaCli;
        packages.freesasaBatch = freesasaBatch;
        packages.rustsasa = rustsasaCli;
        packages.lahuta = lahutaCli;

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            zig
            zsasaCli
            zsasaVersioned06
            zsasaVersioned09
            freesasaCli
            freesasaBatch
            rustsasaCli
            lahutaCli
            python
            uv
            hyperfine
            git
            julia
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
            echo "- versioned zsasa CLIs: zsasa-0.6.0, zsasa-0.9.0"
            echo "- PDBTools.jl wrapper: julia --project=scripts/julia/pdbtools_sasa scripts/benchlib/pdbtools_sasa.jl"
            echo "- Run: python scripts/check_scaffold.py"
            echo "- Dry run full validation: uv run python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run"
          '';
        };
      }
    );
}
