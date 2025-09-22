def getMsiInstallerPath(path){
    def msiFiles = findFiles(glob: "${path}/*.msi")
    if(msiFiles.size()==0){
        error "No .msi file found in ${path}"
    }
    if(msiFiles.size()>1){
        error "more than one .msi file found ${path}"
    }
    return msiFiles[0].path
}

pipeline {
    agent none
    parameters {
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG_X86_64', defaultValue: false, description: 'Create a Apple Application Bundle DMG for Intel based Macs')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG_ARM64', defaultValue: false, description: 'Create a Apple Application Bundle DMG for Apple Silicon')
        booleanParam(name: 'PACKAGE_WINDOWS_INSTALLER', defaultValue: false, description: 'Create a standalone wix based .msi installer')
    }
    stages{
        stage('Building and Testing'){
            stages{
                stage('Build and Test'){
                    environment{
                        PIP_CACHE_DIR='/tmp/pipcache'
                        UV_TOOL_DIR='/tmp/uvtools'
                        UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                        UV_CACHE_DIR='/tmp/uvcache'
                    }
                    agent {
                        docker{
                            image 'python'
                            label 'docker && linux && x86_64'
                            args '--mount source=gce_cache,target=/tmp'
                        }

                    }
                    stages{
                        stage('Setup CI Environment'){
                            steps{
                                sh(
                                    label: 'Create virtual environment with packaging in development mode',
                                    script: '''python3 -m venv bootstrap_uv
                                               bootstrap_uv/bin/pip install --disable-pip-version-check uv
                                               bootstrap_uv/bin/uv venv venv --clear
                                               UV_PROJECT_ENVIRONMENT=./venv bootstrap_uv/bin/uv sync --group ci
                                               bootstrap_uv/bin/uv pip install --python=./venv/bin/python uv
                                               rm -rf bootstrap_uv
                                            '''
                               )
                            }
                        }
                        stage('Run Tests'){
                            parallel{
                                stage('Task Scanner'){
                                    steps{
                                        recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'tripwire/**/*.py', normalTags: 'TODO')])
                                    }
                                }
                                stage('Ruff') {
                                    steps{
                                        catchError(buildResult: 'SUCCESS', message: 'Ruff found issues', stageResult: 'UNSTABLE') {
                                            sh(
                                             label: 'Running Ruff',
                                             script: '''./venv/bin/uv run ruff check --config=pyproject.toml -o reports/ruffoutput.txt --output-format pylint --exit-zero
                                                        ./venv/bin/uv run ruff check --config=pyproject.toml -o reports/ruffoutput.json --output-format json
                                                    '''
                                             )
                                        }
                                    }
                                    post{
                                        always{
                                            recordIssues(tools: [pyLint(pattern: 'reports/ruffoutput.txt', name: 'Ruff')])
                                        }
                                    }
                                }
                                stage('MyPy'){
                                    steps{
                                        catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
                                            tee('logs/mypy.log'){
                                                sh(label: 'Running MyPy',
                                                   script: './venv/bin/uv run mypy -p gce --html-report reports/mypy/html'
                                                )
                                            }
                                        }
                                    }
                                    post {
                                        always {
                                            recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])
                                            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                                        }
                                    }
                                }
                            }
                        }
                    }
                    post {
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'venv/', type: 'INCLUDE'],
                                    [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                ]
                            )
                        }
                    }
                }
            }
        }
        stage('Package'){
            when{
                anyOf{
                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_X86_64
                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_ARM64
                    equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                }
            }
            parallel{
                stage('Mac Application Bundle x86_64'){
                    when{
                        equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_X86_64
                        beforeAgent true
                    }
                    stages{
                        stage('Build Application Bundle'){
                            agent{
                                label 'mac && python3 && x86_64'
                            }
                            steps{
                                sh(label: 'Creating a .dmg installer', script: 'scripts/create_mac_distrib.sh')
                                archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_X86_64'
                            }
                            post{
                                cleanup{
                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                }
                            }
                        }
                        stage('Verify Bundle'){
                            agent{
                                label 'mac && python3 && x86_64'
                            }
                            steps{
                                unstash 'APPLE_APPLICATION_X86_64'
                                sh "hdiutil verify \"${findFiles(glob: 'dist/*.dmg')[0].path}\""
                            }
                            post{
                                cleanup{
                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                }
                            }
                        }
                    }
                }
                stage('Mac Application Bundle ARM64'){
                    when{
                        equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_ARM64
                        beforeAgent true
                    }
                    stages{
                        stage('Build Application Bundle'){
                            agent{
                                label 'mac && python3 && arm64'
                            }
                            steps{
                                sh(label: 'Creating a .dmg installer', script: 'scripts/create_mac_distrib.sh')
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_ARM64'
                                }
                                cleanup{
                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                }
                            }
                        }
                        stage('Verify Bundle'){
                            agent{
                                label 'mac && python3 && arm64'
                            }
                            steps{
                                unstash 'APPLE_APPLICATION_ARM64'
                                sh "hdiutil verify \"${findFiles(glob: 'dist/*.dmg')[0].path}\""
                            }
                            post{
                                cleanup{
                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                }
                            }
                        }
                    }
                }
                stage('Windows Installer for x86_64'){
                    when{
                        equals expected: true, actual: params.PACKAGE_WINDOWS_INSTALLER
                        beforeAgent true
                    }
                    environment{
                        PIP_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\pipcache'
                        UV_TOOL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvtools'
                        UV_PYTHON_INSTALL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvpython'
                        UV_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvcache'
                        VC_RUNTIME_INSTALLER_LOCATION='c:\\msvc_runtime'
                    }
                    stages{
                        stage('Create .msi Installer'){
                            agent {
                               dockerfile {
                                   filename 'ci/docker/windows/Dockerfile'
                                   label 'windows && x86_64 && docker'
                                   args "--mount type=volume,source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR} " \
                                      + "--mount type=volume,source=pipcache,target=${env.PIP_CACHE_DIR} " \
                                      + "--mount type=volume,source=uv_cache_dir,target=${env.UV_CACHE_DIR} " \
                                      + "--mount type=volume,source=msvc-runtime,target=${env.VC_RUNTIME_INSTALLER_LOCATION}"
                               }
                            }
                            steps{
                                bat 'powershell scripts/create-windows-distribution.ps1'
                                archiveArtifacts artifacts: 'dist/*.msi', fingerprint: true
                                stash includes: 'dist/*.msi', name: 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                            }
                            post{
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'build/', type: 'INCLUDE'],
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                        stage('Test .msi Installer'){
                            agent {
                                docker {
                                    args '-u ContainerAdministrator'
                                    image 'mcr.microsoft.com/windows/servercore:ltsc2022'
                                    label 'windows && docker && x86_64'
                                }
                            }
                            options {
                                skipDefaultCheckout true
                            }
                            stages{
                                stage('Checkout Installer'){
                                    steps{
                                        unstash 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                                    }
                                }
                                stage('Install msi file'){
                                    environment {
                                        MSI_INSTALLER = getMsiInstallerPath('dist')
                                    }
                                    steps{
                                        powershell(
                                            label: 'Installing msi file',
                                            script: '''[void](New-Item -ItemType Directory -Force -Path logs)
                                                       Write-Host "Installing $Env:MSI_INSTALLER"
                                                       msiexec /i $Env:MSI_INSTALLER /qn /norestart /L*v! logs\\msiexec.log
                                                       '''
                                        )
                                        powershell(
                                            label: 'Show installed applications',
                                            script: 'Get-WmiObject -Class Win32_Product'
                                        )
                                        bat('powershell ci/jenkins/scripts/ensure_application_installed_property.ps1')
                                    }
                                    post{
                                        always{
                                            archiveArtifacts artifacts: 'logs/msiexec.log'
                                        }
                                    }
                                }
                                stage('Uninstall'){
                                    environment {
                                        APP_NAME='Galatea Config Editor'
                                    }
                                    steps{
                                        powershell(
                                            label: 'Uninstall',
                                            script: '''$app = Get-WmiObject -Class Win32_Product -Filter "Name = \"\"$Env:APP_NAME\"\""
                                                       Write-Host "Uninstalling $app"
                                                       $app.Uninstall()
                                                       Get-WmiObject -Class Win32_Product
                                                    '''
                                       )
                                       bat('powershell ci/jenkins/scripts/ensure_application_uninstalled.ps1')
                                    }
                                }
                            }
                            post{
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}