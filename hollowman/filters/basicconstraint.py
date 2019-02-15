from marathon import MarathonConstraint

from hollowman.marathonapp import AsgardApp


class BasicConstraintFilter:
    workload_constraint = MarathonConstraint.from_json(
        "workload:LIKE:general".split(":")
    )

    def write(self, user, request_app: AsgardApp, app):
        if not request_app.has_constraint(self.workload_constraint.field):
            request_app.constraints.append(self.workload_constraint)

        return request_app
