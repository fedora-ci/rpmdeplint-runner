podTemplate(
    name: 'openshift-pod',
    label: 'openshift-pod',
    cloud: 'openshift',
    serviceAccount: 'jenkins-osci',
    idleMinutes: 0,
    namespace: 'osci',
//     yaml: downstreamUtils.nodeSelector2Yaml(), -- this is just weird...
    containers: [
        containerTemplate(
            name: 'jnlp',
            alwaysPullImage: false,
            image: 'registry.fedoraproject.org/fedora:32',
            ttyEnabled: false,
            args: '${computer.jnlpmac} ${computer.name}',
            envVars: [
                envVar(key: 'GIT_SSL_NO_VERIFY', value: 'true')
            ],
            command: '',
            resourceRequestCpu: '300m',
            resourceLimitCpu: '500m',
            resourceRequestMemory: '256Mi',
            resourceLimitMemory: '1Gi',
            workingDir: '/workDir'
        )
    ]
)
