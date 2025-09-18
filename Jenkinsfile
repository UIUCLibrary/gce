pipeline {
    agent none
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
    }
}