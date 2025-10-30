def createUVConfig(){
    if (isUnix()){
        if(! fileExists('ci/jenkins/scripts/create_uv_config.sh')){
            checkout scm
        }
        return sh(label: 'Setting up uv.toml config file', script: 'sh ci/jenkins/scripts/create_uv_config.sh $UV_INDEX_URL $UV_EXTRA_INDEX_URL', returnStdout: true).trim()
    } else {
        if(! fileExists('ci/jenkins/scripts/new-uv-global-config.ps1')){
            checkout scm
        }
        return powershell(label: 'Setting up uv.toml config file', script: 'ci/jenkins/scripts/new-uv-global-config.ps1 $env:UV_INDEX_URL $env:UV_EXTRA_INDEX_URL', returnStdout: true).trim()
    }

}

def getVersion(){
    node(){
        checkout scm
        return readTOML( file: 'pyproject.toml')['project']['version']
    }
}
def getNexusServer(){
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['server']['urls']
            }
        }
    }
}
def getStandAloneRepos(){
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['publicReleases']['repos']
            }
        }
    }
}

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
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG_X86_64', defaultValue: false, description: 'Create a Apple Application Bundle DMG for Intel based Macs')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG_ARM64', defaultValue: false, description: 'Create a Apple Application Bundle DMG for Apple Silicon')
        booleanParam(name: 'PACKAGE_WINDOWS_INSTALLER', defaultValue: false, description: 'Create a standalone wix based .msi installer')
        booleanParam(name: 'DEPLOY_STANDALONE_PACKAGERS', defaultValue: false, description: 'Deploy standalone packages')
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
                        UV_CONFIG_FILE=createUVConfig()
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            args '--mount source=gce_cache,target=/tmp'
                        }
                    }
                    when{
                        equals expected: true, actual: params.RUN_CHECKS
                        beforeAgent true
                    }
                    stages{
                        stage('Setup CI Environment'){
                            steps{
                                sh(
                                    label: 'Create virtual environment with packaging in development mode',
                                    script: 'uv sync --group ci'
                               )
                            }
                        }
                        stage('Run Tests'){
                            parallel{
                                stage('uv-secure'){
                                    steps{
                                        catchError(buildResult: 'SUCCESS', message: 'uv-secure found issues', stageResult: 'UNSTABLE') {
                                            sh(label: 'Audit Requirement Freeze File', script: 'uv run --only-group=audit-dependencies --frozen --isolated uv-secure --disable-cache uv.lock')
                                        }
                                    }
                                }
                                stage('Task Scanner'){
                                    steps{
                                        recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'src/**/*.py', normalTags: 'TODO')])
                                    }
                                }
                                stage('Ruff') {
                                    steps{
                                        catchError(buildResult: 'SUCCESS', message: 'Ruff found issues', stageResult: 'UNSTABLE') {
                                            sh(
                                             label: 'Running Ruff',
                                             script: '''uv run ruff check --config=pyproject.toml -o reports/ruffoutput.txt --output-format pylint --exit-zero
                                                        uv run ruff check --config=pyproject.toml -o reports/ruffoutput.json --output-format json
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
                                stage('PyTest'){
                                    environment{
                                        PYTHONFAULTHANDLER='1'
                                        QT_QPA_PLATFORM='offscreen'
                                    }
                                    steps{
                                        catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
                                            sh(script: 'uv run coverage run --parallel-mode --source=src -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no')
                                        }
                                    }
                                    post {
                                        always {
                                            junit(allowEmptyResults: true, testResults: 'reports/tests/pytest/pytest-junit.xml')
                                            stash(allowEmpty: true, includes: 'reports/tests/pytest/*.xml', name: 'PYTEST_UNIT_TEST_RESULTS')
                                        }
                                    }
                                }
                                stage('MyPy'){
                                    steps{
                                        catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
                                            tee('logs/mypy.log'){
                                                sh(label: 'Running MyPy',
                                                   script: 'uv run mypy -p gce --html-report reports/mypy/html'
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
                        always{
                            sh(label:'combining coverage data and creating reports',
                               script: '''uv run coverage combine
                                          uv run coverage xml -o reports/coverage.xml
                                          uv run coverage html -d reports/coverage
                                       '''
                            )
                            stash includes: 'reports/coverage.xml', name: 'COVERAGE_REPORT_DATA'
                            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
                        }
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'uv.toml', type: 'INCLUDE'],
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
                    equals expected: true, actual: params.PACKAGE_WINDOWS_INSTALLER
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
                            environment{
                                UV_CONFIG_FILE=createUVConfig()
                                PYINSTALLER_CONFIG_DIR="${env.WORKSPACE}/pyinstaller_config"
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
                            options {
                                skipDefaultCheckout true
                            }
                            steps{
                                unstash 'APPLE_APPLICATION_X86_64'
                                sh "hdiutil verify \"${findFiles(glob: 'dist/*.dmg')[0].path}\""
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
                            environment{
                                UV_CONFIG_FILE=createUVConfig()
                                PYINSTALLER_CONFIG_DIR="${env.WORKSPACE}/pyinstaller_config"
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
                            options {
                                skipDefaultCheckout true
                            }
                            steps{
                                unstash 'APPLE_APPLICATION_ARM64'
                                sh "hdiutil verify \"${findFiles(glob: 'dist/*.dmg')[0].path}\""
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
                            environment{
                                UV_CONFIG_FILE=createUVConfig()
                            }
                            options{
                                timeout(time: 10, unit: 'MINUTES')
                            }
                            steps{
                                bat 'powershell scripts/create-windows-distribution.ps1'
                                archiveArtifacts artifacts: 'dist/*.msi', fingerprint: true
                                stash includes: 'dist/*.msi', name: 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                                stash includes: 'ci/jenkins/scripts/**', name: 'JENKINS_SCRIPTS'
                            }
                            post{
                                failure{
                                    archiveArtifacts artifacts: 'build/**/CPackConfig.cmake,build/**/wix.log'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'uv.toml', type: 'INCLUDE'],
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
                                        unstash 'JENKINS_SCRIPTS'
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
                                       unstash 'JENKINS_SCRIPTS'
                                       bat('powershell ci/jenkins/scripts/ensure_application_uninstalled.ps1')
                                    }
                                }
                            }
                            post{
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'ci/', type: 'INCLUDE'],
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
        stage('Deploy'){
            parallel{
                stage('Deploy Standalone'){
                    agent {
                        label 'linux'
                    }
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_STANDALONE_PACKAGERS
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_X86_64
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG_ARM64
                                equals expected: true, actual: params.PACKAGE_WINDOWS_INSTALLER
                            }
                        }
                        beforeAgent true
                        beforeInput true
                        beforeOptions true
                    }
                    options{
                        skipDefaultCheckout true
                    }
                    input {
                        message 'Upload to Nexus server?'
                        parameters {
                            credentials credentialType: 'com.cloudbees.plugins.credentials.common.StandardCredentials', defaultValue: 'jenkins-nexus', name: 'NEXUS_CREDS', required: true
                            choice(
                                choices: getNexusServer(),
                                description: 'server url.',
                                name: 'NEXUS_SERVER_URL'
                            )
                            choice(
                                choices: getStandAloneRepos(),
                                description: 'Repository to use.',
                                name: 'REPO'
                            )
                            string defaultValue: "gce/${getVersion()}", description: 'subdirectory to store artifact', name: 'archiveFolder'
                        }
                    }
                    steps{
                        script{
                            if(params.PACKAGE_MAC_OS_STANDALONE_DMG_X86_64){
                                unstash 'APPLE_APPLICATION_X86_64'
                            }
                            if(params.PACKAGE_MAC_OS_STANDALONE_DMG_ARM64){
                                unstash 'APPLE_APPLICATION_ARM64'
                            }
                            if(params.PACKAGE_WINDOWS_INSTALLER){
                                unstash 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                            }
                            def parts = [
                                '-F \'raw.directory=gce\'',
                            ]
                            findFiles(glob: 'dist/**/*.*').eachWithIndex{ file, index ->
                                parts += "-F 'raw.asset${index+1}=@${file.path}'"
                                parts += "-F 'raw.asset${index+1}.filename=${file.name}'"
                            }
                            withEnv(["NEXUS_URL=${NEXUS_SERVER_URL}/service/rest/v1/components?repository=${REPO}"]){
                                withCredentials([usernamePassword(credentialsId: NEXUS_CREDS, passwordVariable: 'NEXUS_PASS', usernameVariable: 'NEXUS_USER')])  {
                                   sh "curl -v -u \$NEXUS_USER:\$NEXUS_PASS -X POST ${parts.join(' ')} \$NEXUS_URL"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
