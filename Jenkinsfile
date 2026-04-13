/**
 * Jenkins Pipeline – Student Management API
 *
 * Stages:
 *  1. Checkout         — pull source, capture git metadata, stash
 *  2. Environment Prep — ensure roku_net network exists (idempotent)
 *  3. Build Images     — build app + test runner images in parallel
 *  4. Code Quality     — flake8 lint + black format check (runs inside test image)
 *  5. Start API        — run Flask container, poll until healthy
 *  6. Smoke Tests      — fast sanity: health + one api transaction
 *  7. Functional Tests — integration tests, parallel workers
 *  8. Contract Tests   — JSON schema + SLA response-time assertions
 * 10. Performance      — Locust 10-user headless load test (30s)
 * 11. Archive Reports  — JUnit XML + HTML reports + Locust CSV
 * 12. Teardown         — ALWAYS: stop API container, remove images
 */

pipeline {

    agent any

    // ── Tuneable parameters ──────────────────────────────────────────────────
    parameters {
        string(name: 'API_PORT',     defaultValue: '5000',     description: 'Host port for the Flask container')
        string(name: 'SLA_MS',       defaultValue: '300',      description: 'Max acceptable response time (ms) for contract tests')
        string(name: 'LOCUST_USERS', defaultValue: '10',       description: 'Concurrent Locust users')
        string(name: 'LOCUST_RATE',  defaultValue: '2',        description: 'Locust user spawn rate per second')
        string(name: 'LOCUST_TIME',  defaultValue: '30s',      description: 'Locust test duration')
    }

    environment {
        APP_IMAGE     = "student-api:${BUILD_NUMBER}"
        TEST_IMAGE    = "student-api-tests:${BUILD_NUMBER}"
        CONTAINER_NAME = "student-api-${BUILD_NUMBER}"
        NETWORK_NAME  = "roku_net"
        API_BASE_URL  = "http://localhost:${params.API_PORT}"
        REPORTS_DIR   = "reports"
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
        ansiColor('xterm')
    }

    // ── Pipeline stages ──────────────────────────────────────────────────────
    stages {

        // ─────────────────────────────────────────────────────────────────────
        // Stage 1 · Checkout
        // ─────────────────────────────────────────────────────────────────────
        stage('1 · Checkout') {
            steps {
                checkout scm

                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    env.GIT_BRANCH_SAFE = env.GIT_BRANCH?.replaceAll('/', '-') ?: 'unknown'
                    env.GIT_AUTHOR     = sh(
                        script: 'git log -1 --pretty=format:"%an"',
                        returnStdout: true
                    ).trim()
                    echo "Branch: ${env.GIT_BRANCH_SAFE}  Commit: ${env.GIT_COMMIT_SHORT}  Author: ${env.GIT_AUTHOR}"

                    sh "mkdir -p ${REPORTS_DIR}"
                }

                stash name: 'source', includes: '**/*', excludes: 'reports/**'
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 2 · Environment Prep
        // ─────────────────────────────────────────────────────────────────────
        stage('2 · Environment Prep') {
            steps {
                sh """
                    echo "==> Ensuring Docker network '${NETWORK_NAME}' exists..."
                    docker network inspect ${NETWORK_NAME} > /dev/null 2>&1 || \
                        docker network create ${NETWORK_NAME}
                    echo "Network ready."

                    echo "==> Cleaning up any leftover containers from previous runs..."
                    docker rm -f ${CONTAINER_NAME} 2>/dev/null || true
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 3 · Build Images  (parallel)
        // Must run before Code Quality so the test image exists for linting
        // ─────────────────────────────────────────────────────────────────────
        stage('3 · Build Images') {
            parallel {
                stage('Build app image') {
                    steps {
                        sh "docker build -t ${APP_IMAGE} -f Dockerfile ."
                    }
                }
                stage('Build test runner image') {
                    steps {
                        sh "docker build -t ${TEST_IMAGE} -f Dockerfile.test ."
                    }
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 4 · Code Quality
        // Runs inside the test image — no Python needed on the Jenkins host.
        // Single-quoted sh -c argument ensures && runs inside the container,
        // not on the Jenkins agent shell.
        // ─────────────────────────────────────────────────────────────────────
        stage('4 · Code Quality') {
            steps {
                sh """
                    echo "==> flake8 lint + black format check (inside test image)..."
                    docker run --rm \
                        -v \$(pwd):/app \
                        -w /app \
                        ${TEST_IMAGE} \
                        sh -c 'flake8 app.py tests/ locustfile.py && black --check --diff app.py tests/ locustfile.py'
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 5 · Start API
        // ─────────────────────────────────────────────────────────────────────
        stage('5 · Start API') {
            steps {
                sh """
                    echo "==> Starting API container..."
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        --network ${NETWORK_NAME} \
                        -p ${params.API_PORT}:5000 \
                        ${APP_IMAGE}

                    echo "==> Polling /health until ready (max 60s)..."
                    for i in \$(seq 1 30); do
                        STATUS=\$(curl -s -o /dev/null -w "%{http_code}" \
                            http://localhost:${params.API_PORT}/health 2>/dev/null || echo "000")
                        if [ "\$STATUS" = "200" ]; then
                            echo "API healthy after \${i} attempts."
                            exit 0
                        fi
                        echo "  Attempt \${i}: status=\${STATUS}, retrying..."
                        sleep 2
                    done
                    echo "ERROR: API did not become healthy in time."
                    docker logs ${CONTAINER_NAME}
                    exit 1
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 6 · Smoke Tests
        // ─────────────────────────────────────────────────────────────────────
        stage('6 · Smoke Tests') {
            steps {
                sh """
                    docker run --rm \
                        --network ${NETWORK_NAME} \
                        -e API_BASE_URL=http://${CONTAINER_NAME}:5000 \
                        -v \$(pwd)/${REPORTS_DIR}:/tests/reports \
                        ${TEST_IMAGE} \
                        pytest tests/test_smoke.py -v \
                            --junitxml=reports/smoke-results.xml \
                            --html=reports/smoke-report.html \
                            --self-contained-html
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 7 · Functional Tests  (parallel workers)
        // ─────────────────────────────────────────────────────────────────────
        stage('7 · Functional Tests') {
            steps {
                sh """
                    docker run --rm \
                        --network ${NETWORK_NAME} \
                        -e API_BASE_URL=http://${CONTAINER_NAME}:5000 \
                        -v \$(pwd)/${REPORTS_DIR}:/tests/reports \
                        ${TEST_IMAGE} \
                        pytest tests/test_functional.py -v \
                            -n auto \
                            --junitxml=reports/functional-results.xml \
                            --html=reports/functional-report.html \
                            --self-contained-html
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 8 · Contract Tests
        // ─────────────────────────────────────────────────────────────────────
        stage('8 · Contract Tests') {
            steps {
                sh """
                    docker run --rm \
                        --network ${NETWORK_NAME} \
                        -e API_BASE_URL=http://${CONTAINER_NAME}:5000 \
                        -e SLA_MS=${params.SLA_MS} \
                        -v \$(pwd)/${REPORTS_DIR}:/tests/reports \
                        ${TEST_IMAGE} \
                        pytest tests/test_contract.py -v \
                            --junitxml=reports/contract-results.xml \
                            --html=reports/contract-report.html \
                            --self-contained-html
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 10 · Performance
        // ─────────────────────────────────────────────────────────────────────
        stage('10 · Performance') {
            steps {
                sh """
                    docker run --rm \
                        --network ${NETWORK_NAME} \
                        -v \$(pwd)/${REPORTS_DIR}:/tests/reports \
                        ${TEST_IMAGE} \
                        locust \
                            -f locustfile.py \
                            --headless \
                            --host http://${CONTAINER_NAME}:5000 \
                            -u ${params.LOCUST_USERS} \
                            -r ${params.LOCUST_RATE} \
                            -t ${params.LOCUST_TIME} \
                            --csv=reports/locust \
                            --html=reports/locust-report.html
                """
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Stage 11 · Archive Reports
        // ─────────────────────────────────────────────────────────────────────
        stage('11 · Archive Reports') {
            steps {
                // Publish JUnit XML results
                junit testResults: "${REPORTS_DIR}/*-results.xml",
                      allowEmptyResults: true

                // Archive all reports as build artifacts
                archiveArtifacts artifacts: "${REPORTS_DIR}/**/*",
                                 allowEmptyArchive: true,
                                 fingerprint: true

                // Publish HTML reports (requires HTML Publisher plugin)
                publishHTML(target: [
                    reportDir:   "${REPORTS_DIR}",
                    reportFiles: 'smoke-report.html,functional-report.html,contract-report.html,locust-report.html',
                    reportName:  'Test Reports',
                    keepAll:     true
                ])
            }
        }

    } // end stages

    // ── Post actions ─────────────────────────────────────────────────────────
    post {

        always {
            // Stage 12 · Teardown — runs regardless of pass/fail
            sh """
                echo "==> Stopping and removing API container..."
                docker stop ${CONTAINER_NAME} 2>/dev/null || true
                docker rm   ${CONTAINER_NAME} 2>/dev/null || true

                echo "==> Removing build images..."
                docker rmi ${APP_IMAGE}  2>/dev/null || true
                docker rmi ${TEST_IMAGE} 2>/dev/null || true

                echo "Teardown complete."
            """
        }

        success {
            echo "✅ Pipeline PASSED — Build #${BUILD_NUMBER} (${env.GIT_COMMIT_SHORT})"
        }

        failure {
            echo "❌ Pipeline FAILED — Build #${BUILD_NUMBER} (${env.GIT_COMMIT_SHORT})"
            sh "docker logs ${CONTAINER_NAME} 2>/dev/null || true"
        }

        unstable {
            echo "⚠️  Pipeline UNSTABLE — some tests may have failed"
        }
    }

} // end pipeline