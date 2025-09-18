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
                                               bootstrap_uv/bin/uv venv venv
                                               UV_PROJECT_ENVIRONMENT=./venv bootstrap_uv/bin/uv sync
                                               bootstrap_uv/bin/uv pip install --python=./venv/bin/python uv
                                               rm -rf bootstrap_uv
                                            '''
                               )
                            }
                        }
                    }
                }
            }
        }
    }
}