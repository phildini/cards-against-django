stage { 'prereq':
    before => Stage['main']
}

# class { 'base':
#     stage => prereq,
# }


include base
include nginx
include redis
include postgres
include python

include js
