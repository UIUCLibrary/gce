"""Generate standalone application.

The resulting application does not require the Python Runtime preinstalled
on the user's machine.
"""

import abc
import argparse
import dataclasses
import functools
import logging
import os.path
import sys
import warnings
import zipfile
from typing import Callable, Dict, Union, Optional, Set, Tuple, LiteralString
import packaging.version
import pathlib
import shutil
import subprocess
import tomllib
import PyInstaller.__main__
import cmake
from jinja2 import Template

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

@dataclasses.dataclass(frozen=True)
class StandalonePackages:
    """Dataclass to hold information about standalone packages."""

    exe: Optional[pathlib.Path] = None
    macos_app: Optional[pathlib.Path] = None
    extras: Dict[str, pathlib] = dataclasses.field(default_factory=dict)

    def __len__(self) -> int:
        count = 0
        for field in dataclasses.fields(self):
            if getattr(self, field.name) is not None:
                count += 1
        return count


def create_standalone_from_spec(specs_file: pathlib.Path, dist: pathlib.Path, work_path: pathlib.Path) -> None:
    """Generate standalone executable application."""
    PyInstaller.__main__.run(
        [
            "--noconfirm",
            str(specs_file),
            "--distpath",
            str(dist),
            "--workpath",
            str(work_path),
            "--clean",
            "--log-level",
            "WARN",
        ]
    )

def generate_spec_file(
    output_file: pathlib.Path, script_name: str, entry_point: pathlib.Path, with_debug=False
):
    """Generate pyinstaller specs file."""
    specs = {
        "entry_points": [entry_point.name],
        "name": script_name,
        "hooks_path": [],
        "pathex": [],
        "debug": with_debug
    }
    hooks_path = os.path.abspath(
        f"{pathlib.Path(__file__).parent / 'hooks'}"
    )
    if os.path.exists(hooks_path):
        specs["hooks_path"].append(hooks_path)
    specs_files = pathlib.Path(output_file)
    dist_path = specs_files.parent
    if not dist_path.exists():
        dist_path.mkdir(parents=True, exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), 'package_spec.py.jinja2'), "r") as f:
        template = Template(f.read())
        specs_files.write_text(template.render(**specs))


def get_arg_parser() -> argparse.ArgumentParser:
    """Generate argument parser."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--dest", default="./dist", type=pathlib.Path)
    arg_parser.add_argument(
        "--license-file", default="LICENSE", type=pathlib.Path
    )
    arg_parser.add_argument(
        "--include-readme", default="README.md", type=pathlib.Path
    )
    arg_parser.add_argument("--build-with-debug", action="store_true")
    arg_parser.add_argument("--include-tab-completions", action="store_true")
    arg_parser.add_argument(
        "--build", default="./build/standalone_distribution", dest="build_path",  type=pathlib.Path
    )
    arg_parser.add_argument("command_name")
    arg_parser.add_argument("entry_point", type=pathlib.Path)

    return arg_parser


def find_standalone_distrib(name: str, path: str) -> Optional[str]:
    """Locate a standalone application with a path."""
    for item in os.scandir(path):
        if not item.is_dir():
            continue
        if item.name == name:
            return item.path
    return None


class GenerateCPackConfig(abc.ABC):
    """CPackConfig builder."""

    def __init__(
        self, package_name: str, source_package_path: str, version_number: str
    ):
        """Create a new GenerateCPackConfig builder object."""
        self.source_package_path = source_package_path
        self.install_path_name = ".."
        self.metadata = {
            "CPACK_PACKAGE_VERSION": version_number,
        }
        self.package_name = package_name
        self._additional_directories: Set[Tuple[str, str]] = (
            set()
        )

    def add_additional_directories(
        self, source: str, packaged_folder: str
    ) -> None:
        """Add additional directories to install package."""
        self._additional_directories.add((source, packaged_folder))

    def set_boilderplate(self) -> None:
        """Set boilerplate metadata."""
        self.metadata["CPACK_PACKAGE_NAME"] = self.package_name
        # self.metadata["CPACK_PACKAGE_FILE_NAME"] = self.source_package_path
        version = self.metadata.get("CPACK_PACKAGE_VERSION")
        if version:
            version_parser = packaging.version.Version(version)
            self.metadata['CPACK_PACKAGE_VERSION_MAJOR'] = version_parser.major
            self.metadata['CPACK_PACKAGE_VERSION_MINOR'] = version_parser.minor
            self.metadata['CPACK_PACKAGE_VERSION_PATCH'] = version_parser.micro
            if version_parser.is_devrelease:
                self.metadata['CPACK_PACKAGE_VERSION'] = \
                    f"{version_parser.major}.{version_parser.minor}.{version_parser.micro}-development.{version_parser.dev}"
            elif version_parser.is_prerelease:
                pre_type, pre_version = version_parser.pre
                label = {
                    "a": "alpha",
                    "b": "beta",
                    "rc": "releasecandidate"
                }.get(pre_type)
                if label:
                    self.metadata['CPACK_PACKAGE_VERSION'] = \
                        f"{version_parser.major}.{version_parser.minor}.{version_parser.micro}-{label}.{pre_version}"
        else:
            warnings.warn("Version not set in metadata")

        def sanitize_path(path: str) -> str:
            return os.path.abspath(path).replace("\\", "\\\\")
        app_root_dir = os.path.abspath(self.source_package_path).replace(
            "\\", "\\\\"
        )
        self.metadata['CPACK_INSTALLED_DIRECTORIES'] = [
                (sanitize_path(source_dir), os.path.split(source_dir)[-1])
                # (sanitize_path(source_dir), package_dir)
                for source_dir, package_dir in (
                {(app_root_dir, self.install_path_name)}.union(
                    self._additional_directories
                )
            )
        ]
        if package_dir := self.metadata.get("CPACK_PACKAGE_DIRECTORY"):
            self.metadata["CPACK_PACKAGE_DIRECTORY"] = sanitize_path(package_dir)
        if license_path := self.metadata.get("CPACK_RESOURCE_FILE_LICENSE"):
            self.metadata["CPACK_RESOURCE_FILE_LICENSE"] = sanitize_path(license_path)
    def build(self) -> Dict[str, str]:
        """Build the contents of a config file to use with cpack."""
        self.set_boilderplate()
        return self.metadata

def package_with_cpack(
    package_name: str,
    build_path: str,
    package_root: str,
    dist: str,
    package_metadata: Dict[str, str],
    cpack_generator: str,
) -> None:
    """Package application using cpack utility, part of CMake."""
    if not os.path.exists(build_path):
        os.makedirs(build_path)
    cpack_file = os.path.join(build_path, "CPackConfig.cmake")
    with open(cpack_file, "w") as f:
        cpack_file_generator = GenerateCPackConfig(
            package_name,
            package_root,
            version_number=package_metadata["version"],
        )
        template_metadata = {**cpack_file_generator.build(), **package_metadata}

        if package_dir := template_metadata.get('CPACK_PACKAGE_DIRECTORY'):
            template_metadata["CPACK_PACKAGE_DIRECTORY"] = os.path.abspath(package_dir).replace("\\", "\\\\")

        if license_path := template_metadata.get("CPACK_RESOURCE_FILE_LICENSE"):
            template_metadata["CPACK_RESOURCE_FILE_LICENSE"] = os.path.abspath(license_path).replace("\\", "\\\\")

        with open(os.path.join(os.path.dirname(__file__), 'CPackConfig.cmake.jinja2'), "r") as templated_f:
            template = Template(templated_f.read())
            f.write(template.render(**template_metadata))
        # f.write(cpack_file_generator.build())
    cpack_cmd = shutil.which("cpack", path=cmake.CMAKE_BIN_DIR)
    if not cpack_cmd:
        raise RuntimeError("unable to locate cpack command")
    subprocess.check_call(
        [cpack_cmd, "--config", cpack_file, "-G", cpack_generator]
    )
    for file in filter(
        lambda item: item.is_file(),
        os.scandir(template_metadata['CPACK_PACKAGE_DIRECTORY']),
    ):
        output_file = os.path.normpath(os.path.join(dist, file.name))
        logger.info(f"Copying {file.path} to {output_file}")
        shutil.copy(file.path, output_file)


def package_with_system_zip(
    package_name: str,
    build_path: str,
    package_root: str,
    dist: str,
    package_metadata: Dict[str, str],
):
    """Package application with the OS's zip file command."""
    zip_file_path = os.path.join(
        "dist",
        f"{package_name}-{package_metadata['version']}-{package_metadata['os_name']}-{package_metadata['architecture']}.zip",
    )
    cwd = "dist"
    zip = shutil.which("zip")
    if not zip:
        raise RuntimeError("Could not find zip command on path")
    zip_command = [
        zip,
        "--symlinks",
        "-r",
        os.path.relpath(zip_file_path, cwd),
        os.path.relpath(dist, cwd),
    ]

    subprocess.check_call(zip_command, cwd=cwd)
    logger.info(f"Created {zip_file_path}")


def package_with_system_tar(
    package_name: str,
    build_path: str,
    package_root: str,
    dist: str,
    package_metadata: Dict[str, str],
):
    """Package application with the OS's tar file."""
    archive_file_path = os.path.join(
        dist,
        f"{package_name}-{package_metadata['version']}-{package_metadata['os_name']}-{package_metadata['architecture']}.tar.gz",
    )
    archive_root = os.path.join(package_root, "..")
    tar = shutil.which("tar")
    if not tar:
        raise RuntimeError("Could not find tar command on path")
    command = [
        tar,
        "-zcv",
        "-h",
        "-f",
        os.path.relpath(archive_file_path, build_path),
        "-C",
        os.path.abspath(archive_root),
        os.path.relpath(package_root, archive_root),
    ]
    subprocess.check_call(command, cwd=build_path)


def package_with_builtin_zip(
    package_name: str,
    build_path: str,
    package_root: str,
    dist: str,
    package_metadata: Dict[str, str],
) -> None:
    """Package application with the builtin Python zipfile library."""
    zip_file_path = os.path.join(
        dist,
        f"{package_name}-{package_metadata['version']}-{package_metadata['os_name']}-{package_metadata['architecture']}.zip",
    )
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_root):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, build_path)
                zipf.write(file_path, arcname)

    logger.info(f"Created {zip_file_path}")

class AbsPackagingStrategy(abc.ABC):
    @abc.abstractmethod
    def generate(self, output_path: pathlib.Path) -> None:
        """Generate package distribution."""

class WindowsWixInstallerCreator(AbsPackagingStrategy):

    def __init__(self, build_path: pathlib.Path, package_path: pathlib.Path, license_file: pathlib.Path, command_name) -> None:
        super().__init__()
        self.build_path = build_path
        self.package_path = package_path
        self.command_name = command_name
        self.license_file = license_file

    def generate(self, output_path: pathlib.Path) -> None:
        saved_license_path = self.package_path / "license.txt"
        shutil.copyfile(self.license_file, saved_license_path)
        def metadata_strategy():
            project_toml_file = "pyproject.toml"
            metadata = {
                "CPACK_RESOURCE_FILE_LICENSE": str(saved_license_path),
                "CPACK_WIX_SIZEOF_VOID_P": 8,
                "CPACK_WIX_VERSION": 4,
                "CPACK_PACKAGE_INSTALL_DIRECTORY": "Galatea Config Editor",
                "CPACK_PACKAGE_DESCRIPTION": "Galatea Config Editor",
                "CPACK_PACKAGE_DIRECTORY": os.path.join(self.build_path, "cpack"),
                # "architecture": platform.machine(),
                # "os_name": platform.system(),
            }

            with open(project_toml_file, "rb") as f:
                toml = tomllib.load(f)
                project = toml.get("project", {})
                version = project.get("version")
                if version:
                    metadata["version"] = version

                if description := project.get("description"):
                    metadata["CPACK_PACKAGE_DESCRIPTION"] = description
                return metadata

        package_distribution(
            "Galatea Config Editor",
            str(output_path),
            build_path=str(self.build_path),
            package_root=os.path.abspath(self.package_path),
            metadata_strategy=metadata_strategy,
            package_strategy=functools.partial(
                package_with_cpack,
                cpack_generator="WIX",
            )
        )


class MacOSBundleCreator(AbsPackagingStrategy):

    def __init__(self, build_path: pathlib.Path, package_path: pathlib.Path, command_name) -> None:
        super().__init__()
        self.build_path = build_path
        self.package_path = package_path
        self.command_name = command_name

    def generate(self, output_path: pathlib.Path) -> None:
        """Generate MacOS .app bundle."""

        def metadata_strategy():
            project_toml_file = "pyproject.toml"
            metadata = {
                "CPACK_PACKAGE_DESCRIPTION": "this is a script",
                "CPACK_PACKAGE_DIRECTORY": os.path.join(self.build_path, "cpack"),
            }

            with open(project_toml_file, "rb") as f:
                toml = tomllib.load(f)
                project = toml.get("project", {})
                version = project.get("version")
                if version:
                    metadata["version"] = version
                    metadata["CPACK_PACKAGE_FILE_NAME"] = f"Galatea Config Editor-{version}-macos-${{CMAKE_HOST_SYSTEM_PROCESSOR}}"

                if description := project.get("description"):
                    metadata["CPACK_PACKAGE_DESCRIPTION"] = description
                return metadata

        package_distribution(
            "Galatea Config Editor",
            str(output_path),
            build_path=str(self.build_path),
            package_root=os.path.abspath(self.package_path),
            metadata_strategy=metadata_strategy,
            package_strategy=functools.partial(
                package_with_cpack,
                cpack_generator="DragNDrop",
            )
        )

class PackageDistributionCreator:
    def __init__(self, output_path: pathlib.Path, packager_strategy: AbsPackagingStrategy) -> None:
        """Create a new PackageDistributionCreator object."""
        self.strategy = packager_strategy
        self.output_path = output_path

    def generate(self) -> None:
        """Package distribution."""
        self.strategy.generate(self.output_path)

def package_distribution(
    package_name: str,
    dist: str,
    build_path: str,
    package_root: str,
    metadata_strategy: Callable[[], Dict[str, str]],
    package_strategy: Callable[
        [str, str, str, str, Dict[str, str]], None
    ],
) -> None:
    """Create a distribution package."""
    package_metadata = metadata_strategy()
    package_strategy(
        package_name, build_path, package_root, dist, package_metadata
    )


def create_completions(entry_point: str, dest: pathlib.Path) -> None:
    """Create cli tab completion files for shells."""
    command = ["register-python-argcomplete", entry_point]
    if sys.platform == "darwin":
        supported_shells = {
            "bash": {"file_name": f"{entry_point}.d"},
            "zsh": {"file_name": f"_{entry_point}"},
            "fish": {"file_name": f"{entry_point}.uvx.fish@"},
        }
    elif sys.platform == "win32":
        supported_shells = {
            "powershell": {"file_name": f"{entry_point}.complete.psm1"}
        }
    else:
        supported_shells = {}
    for shell in supported_shells:
        full_command = command + ["--shell", shell]
        result = subprocess.run(full_command, capture_output=True, check=True)
        output_path = os.path.join(dest, shell)
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        file_name = supported_shells[shell]["file_name"]
        completion_file = os.path.join(output_path, file_name)
        with open(completion_file, "w") as f:
            f.write(result.stdout.decode())


def include_extra_files(
    args: argparse.Namespace,
    dest: Union[LiteralString, str | bytes],
) -> None:
    """Include extra file with the package."""
    if os.path.exists(args.license_file):
        shutil.copy(args.license_file, dest)
    else:
        logger.warning("Unable to locate license file %s.", args.license_file)

    if os.path.exists(args.include_readme):
        logger.debug(
            "Found readme file %s. Including it in package",
            args.include_readme,
        )
        shutil.copy(args.include_readme, dest)

class AbsPackageBuilderStrategy(abc.ABC):
    """Abstract package builder strategy."""

    @abc.abstractmethod
    def create(self, dest: pathlib.Path) -> StandalonePackages:
        """Create standalone applications."""

class PackageWithPyInstaller(AbsPackageBuilderStrategy):
    """Build standalone application with PyInstaller."""

    def __init__(
        self,
        command_name: str,
        entry_point: pathlib.Path,
        work_path: pathlib.Path = pathlib.Path("build/standalone/work_path")
    ) -> None:
        """Create a new PackageWithPyInstaller object."""
        super().__init__()
        self.work_path = work_path
        self.command_name = command_name
        self.entry_point = entry_point
        self.build_with_debug = False
        self.source_path = os.getcwd()
        self.include_tab_completions = False

    @property
    def specs_file(self) -> pathlib.Path:
        return self.work_path / f"{self.command_name}.spec"

    def find_standalone_dist(self, path: pathlib.Path) -> StandalonePackages:
        """Locate a standalone application with a path."""
        packages = {}
        for item in os.scandir(path):
            if all([item.is_dir(), item.name.endswith(".app")]):
                packages["macos_app"] =  pathlib.Path(item.path)
                continue

            if all([item.is_dir(), item.name == self.command_name, os.access(item.path, os.X_OK)]):
                packages["exe"] =  pathlib.Path(item.path)

        return StandalonePackages(**packages)


    def create(self, dest: pathlib.Path) -> StandalonePackages:
        """Create standalone applications."""
        if self.command_name is None:
            raise ValueError("command_name must be set first")

        generate_spec_file(
            self.specs_file,
            script_name=self.command_name,
            entry_point=self.entry_point,
            with_debug=self.build_with_debug
        )
        shutil.copy(self.entry_point, self.work_path)
        logger.debug(f"Creating standalone based on generated specs file: {self.specs_file}")
        create_standalone_from_spec(
            self.specs_file,
            dist=dest,
            work_path=self.work_path
        )

        logger.debug(f"Creating standalone applications in {dest}")
        packages = self.find_standalone_dist(path=dest)
        if self.include_tab_completions:
            cli_completions = pathlib.Path(dest, "extras", "cli_completion")
            create_completions(self.command_name, cli_completions.absolute())
            packages.extras["cli_completion"] = cli_completions
        return packages

class StandaloneBuilder:
    """Build standalone application."""

    def __init__(self, dest: pathlib.Path, packager_strategy: AbsPackageBuilderStrategy) -> None:
        """Create a new StandaloneBuilder object."""
        self.strategy = packager_strategy
        self.dest = dest

    def create(self) -> StandalonePackages:
        """Create standalone applications."""
        return self.strategy.create(dest=self.dest)


def main() -> None:
    """Start main entry point."""
    args = get_arg_parser().parse_args()
    if os.path.exists(args.build_path):
        logger.debug("removing existing build path")
        shutil.rmtree(args.build_path)

    work_path = args.build_path / "work_path"
    work_path.mkdir(parents=True, exist_ok=True)

    package_path = args.dest / "standalone_applications"
    package_path.mkdir(parents=True, exist_ok=True)

    packager_with_pyinstaller = PackageWithPyInstaller(
        command_name=args.command_name,
        entry_point=args.entry_point,
        work_path=work_path
    )

    builder = StandaloneBuilder(
        dest=package_path,
        packager_strategy=packager_with_pyinstaller
    )
    packages = builder.create()
    if len(packages) == 0:
        raise FileNotFoundError("No standalone distribution created")

    # include_extra_files(args, dest=work_path)

    if all([packages.exe is not None, sys.platform == "win32"]):
        packager_strategy = WindowsWixInstallerCreator(
            build_path=args.build_path,
            package_path=packages.exe,
            command_name=args.command_name,
            license_file=args.license_file,
        )
        package_output_path = args.dest
        packager = PackageDistributionCreator(
            package_output_path,
            packager_strategy=packager_strategy
        )
        logger.debug(f"Creating Windows executable in {package_output_path}")
        package_output_path.mkdir(parents=True, exist_ok=True)
        packager.generate()
        logger.info(f"Creating Windows executable created in {package_output_path}")

    if all([packages.macos_app is not None, sys.platform == "darwin"]):
        package_output_path = args.dest
        packager_strategy = MacOSBundleCreator(
            build_path=args.build_path,
            package_path=packages.macos_app,
            command_name=args.command_name
        )
        packager = PackageDistributionCreator(
            package_output_path,
            packager_strategy=packager_strategy
        )
        logger.debug(f"Creating MacOS Bundle in {package_output_path}")
        package_output_path.mkdir(parents=True, exist_ok=True)
        packager.generate()
        logger.info(f"Creating MacOS Bundle created in {package_output_path}")


if __name__ == "__main__":
    main()
