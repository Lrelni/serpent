import cProfile
import main


def profile():
    cProfile.run("main.main()", "profile_results")


if __name__ == "__main__":
    profile()
