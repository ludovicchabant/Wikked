from invoke import Collection
from monkeys.release import makerelease


ns = Collection()
ns.add_task(makerelease, name='release')
