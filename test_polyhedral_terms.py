
import unittest
import logging

from PolyhedralContracts import Var, Term, TermSet


class TestTerms(unittest.TestCase):
    def test_one_term_not_simpl(self):
        """A term that cannot be simplified"""
        logging.info("*** Begin test")
        terml_a = TermSet([Term(variables={Var('o'):1}, constant=-1)])
        ref = terml_a.copy()
        terml_b = TermSet([Term(variables={Var('i'):1,Var('o'):-1}, constant=0)])
        logging.info(terml_a)
        logging.info(terml_b)
        terml_a.abduceWithContext(terml_b, {Var('o')})
        logging.info("Term after abduction")
        logging.info(terml_a)
        self.assertEqual(terml_a, ref)

    def test_one_term_simpl(self):
        """A term that can be simplified with the only helper in the list"""
        logging.info("*** Begin test")
        terml_a = TermSet([Term(variables={Var('o'):1}, constant=-1)])
        terml_b = TermSet([Term(variables={Var('i'):-1,Var('o'):1}, constant=0)])
        logging.info(terml_a)
        logging.info(terml_b)
        terml_a.abduceWithContext(terml_b, {Var('o')})
        logging.info(terml_a)
        ref = TermSet([Term(variables={Var('i'):1}, constant=-1)])
        self.assertEqual(terml_a, ref)
    
    def test_two_term_simpl(self):
        """A term that can be simplified with one of two terms in the list"""
        logging.info("*** Begin test")
        terml_a = TermSet([Term(variables={Var('o'):1}, constant=-1)])
        terml_b = TermSet([Term(variables={Var('i'):-1,Var('o'):1}, constant=0), Term(variables={Var('o_a'):-1,Var('o'):1}, constant=0)])
        logging.info(terml_a)
        logging.info(terml_b)
        terml_a.abduceWithContext(terml_b, {Var('o')})
        logging.info(terml_a)
        ref = TermSet([Term(variables={Var('i'):1}, constant=-1)])
        self.assertEqual(terml_a, ref)


if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    unittest.main()