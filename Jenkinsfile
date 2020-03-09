#!groovy

@Library('github.com/msrb/jenkins-pipeline-library@image-push') _

def imageName = ''


pipeline {

    agent {
        node {
            label 'fedora-ci-agent'
        }
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                 buildImageAndPushToRegistry(
                    imageName: 'quay.io/msrb/rpmdeplint',
                    imageTag: '8f3acb7',
                    pushSecret: 'msrb-quay',
                    gitUrl: 'https://github.com/fedora-ci/rpmdeplint-image.git',
                    gitRef: 'master',
                    buildName: 'rpmdeplint-image',
                    openshiftProject: 'osci'
                 )
            }
        }

        stage('Test') {
            steps {
                echo 'Test...'
            }
        }

        stage('Push') {
            steps {
                echo 'Push...'
            }
        }

        stage('Open Pull Requests') {
            when {
                expression { env.BRANCH_NAME == 'master' }
            }
            steps {
                echo 'Open Pull Requests...'
            }
        }

        stage('Add GitHub Comment') {
            when {
                expression { env.BRANCH_NAME != 'master' }
            }
            steps {
                echo 'Add GitHub Comment...'
            }
        }
    }
}
