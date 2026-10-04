# Ejecutor: the body of an email draft

At the leaf `ejecutar`, the body of an email draft is the text you write. `FIN-POL-004 §6` sets
its tone for every collection message, and the same tone applies to every draft: courteous, in
writing, copied to the seller.

## Structure

Write the body in Spanish, in this order and with nothing else:

1. A greeting that names the recipient by the `recipient` parameter.
2. One sentence that states the business situation: the payment delay, overdue balance,
   or supply issue that led to this communication, as the action's `description` provides
   context. Do not describe the system action, do not mention drafts or internal tools.
3. One sentence that requests the recipient to contact their account executive to
   coordinate regularisation of the outstanding balance or to address the situation.
4. A closing that offers to talk.

## Rules

1. Write no figure: no amount, percentage, count of days or count of units. The only digits
   allowed are in identifiers copied from `parameters`.
2. Return the body alone, as plain text: no JSON, no field name, no subject line.
3. Write no threat, no deadline and no consequence the action does not name.
4. Write no sentence about the cause or about other customers.
